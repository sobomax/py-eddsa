import unittest

import eddsa


class EddsaTests(unittest.TestCase):
    def test_constants(self):
        self.assertEqual(eddsa.ED25519_KEY_LEN, 32)
        self.assertEqual(eddsa.ED25519_SIG_LEN, 64)
        self.assertEqual(eddsa.X25519_KEY_LEN, 32)

    def test_ed25519_sign_and_verify(self):
        sec = bytes(range(32))
        data = b"py-eddsa test message"
        pub = eddsa.ed25519_genpub(sec)
        sig = eddsa.ed25519_sign(sec, pub, data)

        self.assertEqual(len(pub), eddsa.ED25519_KEY_LEN)
        self.assertEqual(len(sig), eddsa.ED25519_SIG_LEN)
        self.assertTrue(eddsa.ed25519_verify(sig, pub, data))
        self.assertFalse(eddsa.ed25519_verify(sig, pub, data + b"!"))

    def test_x25519_shared_secret(self):
        alice = bytes(range(32))
        bob = bytes(reversed(range(32)))

        alice_pub = eddsa.x25519_base(alice)
        bob_pub = eddsa.x25519_base(bob)

        self.assertEqual(eddsa.x25519(alice, bob_pub), eddsa.x25519(bob, alice_pub))

    def test_ed25519_to_x25519_conversion(self):
        ed_sec = bytes((i * 7) & 0xff for i in range(32))
        ed_pub = eddsa.ed25519_genpub(ed_sec)

        x_sec = eddsa.sk_ed25519_to_x25519(ed_sec)
        x_pub = eddsa.pk_ed25519_to_x25519(ed_pub)

        self.assertEqual(eddsa.x25519_base(x_sec), x_pub)

    def test_obsolete_aliases(self):
        sec = bytes(range(32))
        data = b"alias test"
        pub = eddsa.eddsa_genpub(sec)
        sig = eddsa.eddsa_sign(sec, pub, data)

        self.assertTrue(eddsa.eddsa_verify(sig, pub, data))
        self.assertEqual(eddsa.DH(sec, eddsa.x25519_base(sec)), eddsa.x25519(sec, eddsa.x25519_base(sec)))
        self.assertEqual(eddsa.eddsa_sk_eddsa_to_dh(sec), eddsa.sk_ed25519_to_x25519(sec))
        self.assertEqual(eddsa.eddsa_pk_eddsa_to_dh(pub), eddsa.pk_ed25519_to_x25519(pub))

    def test_length_validation(self):
        with self.assertRaises(ValueError):
            eddsa.ed25519_genpub(b"short")
        with self.assertRaises(ValueError):
            eddsa.ed25519_sign(bytes(32), b"short", b"data")
        with self.assertRaises(ValueError):
            eddsa.ed25519_verify(bytes(64), b"short", b"data")
        with self.assertRaises(ValueError):
            eddsa.x25519(bytes(32), b"short")


if __name__ == "__main__":
    unittest.main()
