package dev.booking.sys

import org.junit.jupiter.api.Test
import org.springframework.beans.factory.annotation.Autowired
import org.springframework.boot.webmvc.test.autoconfigure.WebMvcTest
import org.springframework.context.annotation.Bean
import org.springframework.context.annotation.Configuration
import org.springframework.context.annotation.Import
import org.springframework.security.core.authority.SimpleGrantedAuthority
import org.springframework.security.oauth2.jwt.JwtDecoder
import org.springframework.security.test.web.servlet.request.SecurityMockMvcRequestPostProcessors.jwt
import org.springframework.test.context.ContextConfiguration
import org.springframework.test.web.servlet.MockMvc
import org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get
import org.springframework.test.web.servlet.request.MockMvcRequestBuilders.post
import org.springframework.test.web.servlet.result.MockMvcResultMatchers.status
import org.springframework.web.bind.annotation.GetMapping
import org.springframework.web.bind.annotation.PostMapping
import org.springframework.web.bind.annotation.RestController

/**
 * The route rules of the real [SecurityConfig] chain (R17, AQ3).
 *
 * The controllers behind the routes are stubs answering 200: what is under test
 * is whether a token reaches them at all, not what they do once reached.
 */
@WebMvcTest
@ContextConfiguration(classes = [SecurityConfigTest.Routes::class])
class SecurityConfigTest {

    @Configuration
    @Import(SecurityConfig::class)
    class Routes {
        @Bean
        fun jwtDecoder(): JwtDecoder = JwtDecoder { error("tokens are supplied by jwt() in these tests") }

        @Bean
        fun stub() = StubController()
    }

    @RestController
    class StubController {
        @GetMapping("/internal/v1/bookings/{ref}/contacts") fun contacts() = "ok"
        @PostMapping("/v1/providers") fun createProvider() = "ok"
        @GetMapping("/v1/bookings") fun myBookings() = "ok"
    }

    @Autowired
    private lateinit var mvc: MockMvc

    private fun scoped(scope: String) = jwt().authorities(SimpleGrantedAuthority("SCOPE_$scope"))

    @Test
    fun `an end-user token cannot read a booking's contacts`() {
        mvc.perform(get("/internal/v1/bookings/0196a000-0000-7000-8000-000000000001/contacts").with(jwt()))
            .andExpect(status().isForbidden)
    }

    @Test
    fun `a token granted the contacts scope can read contacts`() {
        mvc.perform(
            get("/internal/v1/bookings/0196a000-0000-7000-8000-000000000001/contacts")
                .with(scoped(SecurityConfig.CONTACTS_SCOPE)),
        ).andExpect(status().isOk)
    }

    @Test
    fun `an unscoped token cannot create a provider`() {
        mvc.perform(post("/v1/providers").with(jwt())).andExpect(status().isForbidden)
    }

    @Test
    fun `the onboarding scope can create a provider, and does not open the contacts route`() {
        mvc.perform(post("/v1/providers").with(scoped(SecurityConfig.ONBOARD_SCOPE))).andExpect(status().isOk)
        mvc.perform(
            get("/internal/v1/bookings/0196a000-0000-7000-8000-000000000001/contacts")
                .with(scoped(SecurityConfig.ONBOARD_SCOPE)),
        ).andExpect(status().isForbidden)
    }

    @Test
    fun `other routes still need only a verified token`() {
        mvc.perform(get("/v1/bookings").with(jwt())).andExpect(status().isOk)
        mvc.perform(get("/v1/bookings")).andExpect(status().isUnauthorized)
    }
}
