/*
 * blink.c — Simple LED blink test to verify toolchain and Pico connection.
 */

#include "pico/stdlib.h"
#include <stdio.h>

#define LED_PIN 25  /* On-board LED on Pico H */

int main(void) {
    stdio_init_all();
    gpio_init(LED_PIN);
    gpio_set_dir(LED_PIN, GPIO_OUT);

    /* Wait for USB serial to be ready */
    sleep_ms(2000);
    printf("PQC Benchmark Suite — Blink Test\n");
    printf("Platform: Raspberry Pi Pico H (RP2040, ARM Cortex-M0+ @ 133MHz)\n");
    printf("If you see this, serial output is working!\n");

    int count = 0;
    while (true) {
        gpio_put(LED_PIN, 1);
        printf("LED ON  (cycle %d)\n", ++count);
        sleep_ms(500);

        gpio_put(LED_PIN, 0);
        printf("LED OFF (cycle %d)\n", count);
        sleep_ms(500);
    }

    return 0;
}
