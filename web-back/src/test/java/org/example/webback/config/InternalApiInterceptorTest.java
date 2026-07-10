package org.example.webback.config;

import org.junit.jupiter.api.Test;
import org.springframework.mock.web.MockHttpServletRequest;
import org.springframework.mock.web.MockHttpServletResponse;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertTrue;

class InternalApiInterceptorTest {

    private static final String TOKEN = "0123456789abcdef0123456789abcdef";
    private final InternalApiInterceptor interceptor = new InternalApiInterceptor(TOKEN);

    @Test
    void acceptsMatchingServiceToken() throws Exception {
        MockHttpServletRequest request = new MockHttpServletRequest();
        request.addHeader(InternalApiInterceptor.TOKEN_HEADER, TOKEN);

        assertTrue(interceptor.preHandle(
                request, new MockHttpServletResponse(), new Object()));
    }

    @Test
    void rejectsMissingServiceToken() throws Exception {
        MockHttpServletResponse response = new MockHttpServletResponse();

        assertFalse(interceptor.preHandle(
                new MockHttpServletRequest(), response, new Object()));
        assertEquals(401, response.getStatus());
    }
}
