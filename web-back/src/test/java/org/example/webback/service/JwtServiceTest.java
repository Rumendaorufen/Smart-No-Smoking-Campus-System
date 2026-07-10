package org.example.webback.service;

import org.junit.jupiter.api.Test;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertThrows;

class JwtServiceTest {

    @Test
    void createsAndVerifiesTokenWithOneConfiguredKey() {
        JwtService service = new JwtService("0123456789abcdef0123456789abcdef");

        String token = service.createToken(42L);

        assertEquals(42L, service.verifyAndGetUserId(token));
    }

    @Test
    void rejectsTokenSignedWithAnotherKey() {
        JwtService issuer = new JwtService("0123456789abcdef0123456789abcdef");
        JwtService verifier = new JwtService("abcdef0123456789abcdef0123456789");

        String token = issuer.createToken(42L);

        assertThrows(IllegalArgumentException.class,
                () -> verifier.verifyAndGetUserId(token));
    }
}
