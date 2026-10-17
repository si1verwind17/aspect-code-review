package dev.booking.worker

import java.util.concurrent.CountDownLatch
import java.util.concurrent.TimeUnit
import kotlin.test.Test
import kotlin.test.assertTrue
import org.springframework.context.annotation.AnnotationConfigApplicationContext
import org.springframework.scheduling.annotation.Scheduled

/**
 * A job blocked indefinitely — the relay waiting on a broker — must not hold back
 * the others.  Runs the real [WorkerScheduling] configuration with two stand-in jobs.
 */
class WorkerSchedulingTest {

    class Jobs {
        val release = CountDownLatch(1)
        val sweepRan = CountDownLatch(3)

        @Scheduled(fixedDelay = 10)
        fun stuckRelay() {
            release.await()
        }

        @Scheduled(fixedDelay = 10)
        fun sweep() {
            sweepRan.countDown()
        }
    }

    @Test
    fun `a blocked job does not starve the other scheduled jobs`() {
        AnnotationConfigApplicationContext().use { context ->
            context.environment.setActiveProfiles("worker")
            context.register(WorkerScheduling::class.java, Jobs::class.java)
            context.refresh()
            val jobs = context.getBean(Jobs::class.java)
            try {
                assertTrue(jobs.sweepRan.await(5, TimeUnit.SECONDS), "the sweep never ran while the relay was blocked")
            } finally {
                jobs.release.countDown()
            }
        }
    }
}
