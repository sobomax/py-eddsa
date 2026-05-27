#include <stdbool.h>
#include <stdint.h>
#include <stdio.h>
#include <time.h>

#include "eddsa.h"


#define MIN_SECONDS 0.2
#define SAMPLES 5
#define RNG_SEED 0xedd5au


static uint8_t sec[ED25519_KEY_LEN];
static uint8_t other_sec[ED25519_KEY_LEN];
static uint8_t msg[256];
static uint8_t pub[ED25519_KEY_LEN];
static uint8_t sig[ED25519_SIG_LEN];
static uint8_t point[X25519_KEY_LEN];
static uint8_t out[ED25519_SIG_LEN];
static volatile uint8_t sink_byte;
static volatile bool sink_bool;
static uint32_t rng_state;


static double
now_seconds(void)
{
    return (double)clock() / (double)CLOCKS_PER_SEC;
}


static uint8_t
rng_byte(void)
{
    rng_state = rng_state * 1664525u + 1013904223u;
    return (uint8_t)(rng_state >> 24);
}


static void
op_ed25519_genpub(void)
{
    ed25519_genpub(out, sec);
    sink_byte ^= out[0];
}


static void
op_ed25519_sign(void)
{
    ed25519_sign(out, sec, pub, msg, sizeof(msg));
    sink_byte ^= out[0];
}


static void
op_ed25519_verify(void)
{
    sink_bool ^= ed25519_verify(sig, pub, msg, sizeof(msg));
}


static void
op_x25519_base(void)
{
    x25519_base(out, sec);
    sink_byte ^= out[0];
}


static void
op_x25519(void)
{
    x25519(out, sec, point);
    sink_byte ^= out[0];
}


static void
op_pk_ed25519_to_x25519(void)
{
    pk_ed25519_to_x25519(out, pub);
    sink_byte ^= out[0];
}


static void
op_sk_ed25519_to_x25519(void)
{
    sk_ed25519_to_x25519(out, sec);
    sink_byte ^= out[0];
}


static double
sample_operation(void (*func)(void), unsigned long loops)
{
    unsigned long i;
    double start = now_seconds();
    for (i = 0; i < loops; i++) {
        func();
    }
    return now_seconds() - start;
}


static double
measure(void (*func)(void))
{
    unsigned long loops = 1;
    double elapsed;
    double best;
    int i;

    do {
        elapsed = sample_operation(func, loops);
        if (elapsed >= MIN_SECONDS) {
            break;
        }
        loops *= 2;
    } while (1);

    best = sample_operation(func, loops);
    for (i = 1; i < SAMPLES; i++) {
        elapsed = sample_operation(func, loops);
        if (elapsed < best) {
            best = elapsed;
        }
    }
    return (double)loops / best;
}


static void
print_result(const char *name, void (*func)(void), bool comma)
{
    double ops = measure(func);
    printf("%s\"%s\":{\"ops_per_second\":%.6f}", comma ? "," : "", name, ops);
}


int
main(void)
{
    size_t i;

    rng_state = RNG_SEED;
    for (i = 0; i < sizeof(sec); i++) {
        sec[i] = rng_byte();
        other_sec[i] = rng_byte();
    }
    for (i = 0; i < sizeof(msg); i++) {
        msg[i] = rng_byte();
    }

    ed25519_genpub(pub, sec);
    ed25519_sign(sig, sec, pub, msg, sizeof(msg));
    x25519_base(point, other_sec);

    printf("{\"benchmarks\":{");
    print_result("ed25519_genpub", op_ed25519_genpub, false);
    print_result("ed25519_sign_256b", op_ed25519_sign, true);
    print_result("ed25519_verify_256b", op_ed25519_verify, true);
    print_result("x25519_base", op_x25519_base, true);
    print_result("x25519", op_x25519, true);
    print_result("pk_ed25519_to_x25519", op_pk_ed25519_to_x25519, true);
    print_result("sk_ed25519_to_x25519", op_sk_ed25519_to_x25519, true);
    printf("}}\n");

    (void)sink_byte;
    (void)sink_bool;
    return 0;
}
