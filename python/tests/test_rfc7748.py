"""
RFC 7748 X25519 test vectors for the eddsa package.

Expected values were taken from the authoritative RFC text
(https://www.rfc-editor.org/rfc/rfc7748.txt, sections 5.2, 6.1, 7) and
independently verified against OpenSSL via python-cryptography
(2026-11-15, see evidence/verify_rfc7748_openssl.py):

- section 5.2 single-shot vector 1: MATCH
- section 5.2 single-shot vector 2 (MSB of u set): MATCH
- section 5.2 iterated test, after 1 iteration: MATCH
- section 5.2 iterated test, after 1000 iterations: MATCH
  (iteration per RFC: (k, u) = (X25519(k, u), old k); result is k)
- section 6.1 Alice public key, Bob public key, shared secret (both
  directions): MATCH

For the small-order input points, OpenSSL (python-cryptography) rejects
the point input outright, so the all-zero expectation there is verified
against the RFC text (section 6.1 / section 7: X25519 produces the
all-zero value for small-order inputs so callers can detect it), not
against OpenSSL.

Only the public eddsa API (x25519, x25519_base) is used.
"""

import os
import unittest

from eddsa import X25519_KEY_LEN, x25519, x25519_base


def h(s):
    return bytes.fromhex(s)


# --- RFC 7748 section 5.2: single-shot vectors ---------------------------
V1_SCALAR = "a546e36bf0527c9d3b16154b82465edd62144c0ac1fc5a18506a2244ba449ac4"
V1_U = "e6db6867583030db3594c1a424b15f7c726624ec26b3353b10a903a6d0ab1c4c"
V1_OUT = "c3da55379de9c6908e94ea4df28d084f32eccf03491c71f754b4075577a28552"

# u[31] = 0x93: most-significant bit of the final byte is set, so this
# vector only passes if the implementation masks it per RFC 7748 section 5.
V2_SCALAR = "4b66e9d4d1b4673c5ad22691957d6af5c11b6421e0ea01d42ca4169e7918ba0d"
V2_U = "e5210f12786811d3f4b7959d0538ae2c31dbe7106fc03c3efc4cd549c715a493"
V2_OUT = "95cbde9476e8907d7aade45cb4b873f88b595a68799fa152e6f8f7647aac7957"

# --- RFC 7748 section 5.2: iterated test ----------------------------------
ITER_INIT = "09" + "00" * 31
ITER1 = "422c8e7a6227d7bca1350b3e2bb7279f7897b87bb6854b783c60e80311ae3079"
ITER1000 = "684cf59ba83309552800ef566f2f4d3c1c3887c49360e3875f2eb94d99532c51"
ITER1000000 = "7c3911e0ab2586fd864497297e575e6f3bc601c0883c30df5f4dd2d24f665424"

# --- RFC 7748 section 6.1: Alice/Bob ECDH example --------------------------
ALICE_SK = "77076d0a7318a57d3c16c17251b26645df4c2f87ebc0992ab177fba51db92c2a"
ALICE_PK = "8520f0098930a754748b7ddcb43ef75a0dbf3a0d26381af4eba4a98eaa9b4e6a"
BOB_SK = "5dab087e624a8a4b79e17f8b83800ee66f3bb1292618b6fd1c2f8b27ff88e0eb"
BOB_PK = "de9edb7d7b7dc1b4d35b61c2ece435373f8343c85b78674dadfc7e146f882b4f"
SHARED = "4a5d9d5ba4ce2de1728e3bf480350f25e07e21c947d19e3376f09b3c1e161742"

# --- small-order input points (RFC 7748 section 7, curve25519 suite) ------
# X25519 always applies an even (in fact, multiple-of-8) scalar, so any
# input point whose order divides 8 yields the all-zero output.
SMALL_ORDER_POINTS = {
    "all-zero u (order-2 point)": "00" * 32,
    "u = 1 (neutral point, order-4 subgroup)": "01" + "00" * 31,
    "e0eb7a7c... (order-8 point, curve25519 test suite)":
        "e0eb7a7c3b41b8ae1656e3faf19fc46ada098deb9c32b1fd866205165f49b800",
}

ZERO = bytes(32)


class Rfc7748X25519Test(unittest.TestCase):
    def test_vector_1(self):
        self.assertEqual(x25519(h(V1_SCALAR), h(V1_U)), h(V1_OUT))

    def test_vector_2_msb_set(self):
        self.assertEqual(x25519(h(V2_SCALAR), h(V2_U)), h(V2_OUT))

    def test_iterated_after_one(self):
        k, u = h(ITER_INIT), h(ITER_INIT)
        k, u = x25519(k, u), k
        self.assertEqual(k, h(ITER1))

    def test_iterated_after_1000(self):
        k, u = h(ITER_INIT), h(ITER_INIT)
        for _ in range(1000):
            k, u = x25519(k, u), k
        self.assertEqual(k, h(ITER1000))

    @unittest.skipUnless(
        os.environ.get("RUN_SLOW_X25519_TESTS"),
        "1,000,000 iterations are optional; enable with RUN_SLOW_X25519_TESTS=1",
    )
    def test_iterated_after_1000000(self):
        k, u = h(ITER_INIT), h(ITER_INIT)
        for _ in range(1_000_000):
            k, u = x25519(k, u), k
        self.assertEqual(k, h(ITER1000000))

    def test_section_6_1_public_keys(self):
        self.assertEqual(x25519_base(h(ALICE_SK)), h(ALICE_PK))
        self.assertEqual(x25519_base(h(BOB_SK)), h(BOB_PK))

    def test_section_6_1_shared_secret(self):
        self.assertEqual(x25519(h(ALICE_SK), h(BOB_PK)), h(SHARED))
        self.assertEqual(x25519(h(BOB_SK), h(ALICE_PK)), h(SHARED))

    def test_small_order_points_all_zero(self):
        for name, u in SMALL_ORDER_POINTS.items():
            for s in (ALICE_SK, BOB_SK, "02" + "00" * 31):
                with self.subTest(point=name, scalar=s[:8]):
                    self.assertEqual(
                        x25519(h(s), h(u)), ZERO,
                        f"small-order input {name} must yield all-zero output",
                    )

    def test_output_length(self):
        self.assertEqual(len(x25519(h(ALICE_SK), h(BOB_PK))), X25519_KEY_LEN)
        self.assertEqual(len(x25519_base(h(ALICE_SK))), X25519_KEY_LEN)


if __name__ == "__main__":
    unittest.main()
