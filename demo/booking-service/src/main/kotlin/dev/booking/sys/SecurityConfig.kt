package dev.booking.sys

import org.springframework.context.annotation.Bean
import org.springframework.context.annotation.Configuration
import org.springframework.http.HttpMethod
import org.springframework.security.config.annotation.web.builders.HttpSecurity
import org.springframework.security.config.annotation.web.configuration.EnableWebSecurity
import org.springframework.security.web.SecurityFilterChain

/**
 * R17: identity comes only from a verified token, and nothing else.
 *
 * There is deliberately no fallback for a missing issuer configuration — Boot
 * requires a `JwtDecoder`, so a deployment without one fails at startup instead
 * of quietly accepting unverified requests.  A misconfigured deployment that
 * dies loudly is the intended behaviour.
 *
 * Two routes are not open to every holder of an issuer token, because a token
 * proves only who the caller is, not that the caller may act at all:
 * - the `/internal/` routes serve customer contact details to a consuming service
 *   (AQ3), so it needs a token granted [CONTACTS_SCOPE] — a client-credentials
 *   grant for that service, never an end-user token.
 * - `POST /v1/providers` makes its caller the new provider's first admin, so it
 *   needs [ONBOARD_SCOPE], granted by the operator who admits a provider.
 * Everything else stays membership-based (BookingAuthorization).
 */
@Configuration
@EnableWebSecurity
class SecurityConfig {

    @Bean
    fun securityFilterChain(http: HttpSecurity): SecurityFilterChain =
        http
            .csrf { it.disable() }
            .authorizeHttpRequests {
                it.requestMatchers("/actuator/**").permitAll()
                it.requestMatchers("/internal/**").hasAuthority("SCOPE_$CONTACTS_SCOPE")
                it.requestMatchers(HttpMethod.POST, "/v1/providers").hasAuthority("SCOPE_$ONBOARD_SCOPE")
                it.anyRequest().authenticated()
            }
            .oauth2ResourceServer { it.jwt { } }
            .build()

    companion object {
        const val CONTACTS_SCOPE = "booking.contacts.read"
        const val ONBOARD_SCOPE = "booking.providers.create"
    }
}
