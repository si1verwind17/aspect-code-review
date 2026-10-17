package dev.booking.worker

import org.springframework.context.annotation.Bean
import org.springframework.context.annotation.Configuration
import org.springframework.context.annotation.Profile
import org.springframework.scheduling.TaskScheduler
import org.springframework.scheduling.annotation.EnableScheduling
import org.springframework.scheduling.concurrent.ThreadPoolTaskScheduler

/**
 * One scheduler thread per background job.
 *
 * Without this bean Boot's virtual-thread scheduler runs every fixed-delay job
 * on a single thread, so a relay pass blocked on an unreachable broker holds back
 * the hold-expiry and auto-complete sweeps for as long as it lasts — and a lapsed
 * hold keeps its capacity the whole time.  With a thread each, a stuck relay
 * delays only the relay.
 */
@Configuration
@Profile("worker")
@EnableScheduling
class WorkerScheduling {

    @Bean
    fun workerTaskScheduler(): TaskScheduler =
        ThreadPoolTaskScheduler().apply {
            poolSize = JOBS
            setThreadNamePrefix("worker-job-")
        }

    companion object {
        /** The relay and the two sweeps in WorkerSchedules. */
        const val JOBS = 3
    }
}
