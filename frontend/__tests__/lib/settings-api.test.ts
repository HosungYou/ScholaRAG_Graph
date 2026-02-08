/**
 * Tests for Settings API client methods
 * v0.13.0: API key management endpoints
 */
export {};

// Mock fetch globally
const mockFetch = jest.fn();
global.fetch = mockFetch;

// Mock Supabase
jest.mock('@/lib/supabase', () => ({
  getSession: jest.fn().mockResolvedValue({
    access_token: 'test-token',
  }),
}));

describe('ApiClient - Settings API', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    mockFetch.mockResolvedValue({
      ok: true,
      status: 200,
      json: () => Promise.resolve({}),
      headers: new Headers({ 'content-type': 'application/json' }),
    });
  });

  describe('getApiKeys', () => {
    it('should send GET request to correct URL', async () => {
      const { default: api } = await import('@/lib/api');

      await api.getApiKeys();

      expect(mockFetch).toHaveBeenCalled();
      const [url, options] = mockFetch.mock.calls[0];

      expect(url).toContain('/api/settings/api-keys');
      expect(options.method).toBeUndefined(); // GET is default
    });

    it('should include authorization header', async () => {
      const { default: api } = await import('@/lib/api');

      await api.getApiKeys();

      const [, options] = mockFetch.mock.calls[0];
      expect(options.headers).toHaveProperty('Authorization', 'Bearer test-token');
    });

    it('should return array of provider statuses', async () => {
      const mockResponse = [
        { provider: 'groq', configured: true, valid: true },
        { provider: 'anthropic', configured: false, valid: false },
      ];

      mockFetch.mockResolvedValue({
        ok: true,
        status: 200,
        json: () => Promise.resolve(mockResponse),
        headers: new Headers({ 'content-type': 'application/json' }),
      });

      const { default: api } = await import('@/lib/api');
      const result = await api.getApiKeys();

      expect(result).toEqual(mockResponse);
    });
  });

  describe('updateApiKeys', () => {
    it('should send PUT request with flat JSON body for keys only', async () => {
      const { default: api } = await import('@/lib/api');
      const keys = { groq: 'gsk_test123', anthropic: 'sk-ant-test456' };

      await api.updateApiKeys(keys);

      expect(mockFetch).toHaveBeenCalled();
      const [url, options] = mockFetch.mock.calls[0];

      expect(url).toContain('/api/settings/api-keys');
      expect(options.method).toBe('PUT');

      if (options.body) {
        const body = JSON.parse(options.body);
        expect(body).toEqual(keys);
        expect(body.groq).toBe('gsk_test123');
        expect(body.anthropic).toBe('sk-ant-test456');
      }
    });

    it('should merge keys and options correctly', async () => {
      const { default: api } = await import('@/lib/api');
      const keys = { groq: 'gsk_test123' };
      const options = { llm_provider: 'anthropic', llm_model: 'claude-sonnet-4-5' };

      await api.updateApiKeys(keys, options);

      const [, requestOptions] = mockFetch.mock.calls[0];
      if (requestOptions.body) {
        const body = JSON.parse(requestOptions.body);
        expect(body).toEqual({
          groq: 'gsk_test123',
          llm_provider: 'anthropic',
          llm_model: 'claude-sonnet-4-5',
        });
      }
    });

    it('should work with options only (no keys)', async () => {
      const { default: api } = await import('@/lib/api');
      const options = { llm_provider: 'groq', llm_model: 'llama-3.3-70b-versatile' };

      await api.updateApiKeys({}, options);

      const [, requestOptions] = mockFetch.mock.calls[0];
      if (requestOptions.body) {
        const body = JSON.parse(requestOptions.body);
        expect(body).toEqual(options);
        expect(body.llm_provider).toBe('groq');
        expect(body.llm_model).toBe('llama-3.3-70b-versatile');
      }
    });

    it('should work with keys only (no options)', async () => {
      const { default: api } = await import('@/lib/api');
      const keys = { openai: 'sk-test789' };

      await api.updateApiKeys(keys);

      const [, requestOptions] = mockFetch.mock.calls[0];
      if (requestOptions.body) {
        const body = JSON.parse(requestOptions.body);
        expect(body).toEqual({ openai: 'sk-test789' });
        expect(body.llm_provider).toBeUndefined();
        expect(body.llm_model).toBeUndefined();
      }
    });

    it('should include authorization header', async () => {
      const { default: api } = await import('@/lib/api');

      await api.updateApiKeys({ groq: 'test' });

      const [, options] = mockFetch.mock.calls[0];
      expect(options.headers).toHaveProperty('Authorization', 'Bearer test-token');
    });

    it('should return response data', async () => {
      const mockResponse = {
        updated: ['groq', 'anthropic'],
        llm_provider: 'anthropic',
        llm_model: 'claude-sonnet-4-5',
      };

      mockFetch.mockResolvedValue({
        ok: true,
        status: 200,
        json: () => Promise.resolve(mockResponse),
        headers: new Headers({ 'content-type': 'application/json' }),
      });

      const { default: api } = await import('@/lib/api');
      const result = await api.updateApiKeys(
        { groq: 'test1', anthropic: 'test2' },
        { llm_provider: 'anthropic', llm_model: 'claude-sonnet-4-5' }
      );

      expect(result).toEqual(mockResponse);
    });
  });

  describe('validateApiKey', () => {
    it('should send POST request with provider and key', async () => {
      const { default: api } = await import('@/lib/api');

      await api.validateApiKey('groq', 'gsk_test123');

      expect(mockFetch).toHaveBeenCalled();
      const [url, options] = mockFetch.mock.calls[0];

      expect(url).toContain('/api/settings/api-keys/validate');
      expect(options.method).toBe('POST');

      if (options.body) {
        const body = JSON.parse(options.body);
        expect(body.provider).toBe('groq');
        expect(body.key).toBe('gsk_test123');
      }
    });

    it('should return validation result for valid key', async () => {
      const mockResponse = {
        provider: 'groq',
        valid: true,
        model: 'llama-3.3-70b-versatile',
      };

      mockFetch.mockResolvedValue({
        ok: true,
        status: 200,
        json: () => Promise.resolve(mockResponse),
        headers: new Headers({ 'content-type': 'application/json' }),
      });

      const { default: api } = await import('@/lib/api');
      const result = await api.validateApiKey('groq', 'gsk_valid_key');

      expect(result).toEqual(mockResponse);
      expect(result.valid).toBe(true);
    });

    it('should return validation result for invalid key', async () => {
      const mockResponse = {
        provider: 'anthropic',
        valid: false,
        error: 'Invalid API key format',
      };

      mockFetch.mockResolvedValue({
        ok: true,
        status: 200,
        json: () => Promise.resolve(mockResponse),
        headers: new Headers({ 'content-type': 'application/json' }),
      });

      const { default: api } = await import('@/lib/api');
      const result = await api.validateApiKey('anthropic', 'invalid_key');

      expect(result).toEqual(mockResponse);
      expect(result.valid).toBe(false);
    });

    it('should handle unsupported provider', async () => {
      const mockResponse = {
        provider: 'unsupported_provider',
        valid: false,
        message: 'Provider not supported',
      };

      mockFetch.mockResolvedValue({
        ok: true,
        status: 200,
        json: () => Promise.resolve(mockResponse),
        headers: new Headers({ 'content-type': 'application/json' }),
      });

      const { default: api } = await import('@/lib/api');
      const result = await api.validateApiKey('unsupported_provider', 'test_key');

      expect(result.valid).toBe(false);
      expect(result.message).toBeTruthy();
    });

    it('should include authorization header', async () => {
      const { default: api } = await import('@/lib/api');

      await api.validateApiKey('groq', 'test');

      const [, options] = mockFetch.mock.calls[0];
      expect(options.headers).toHaveProperty('Authorization', 'Bearer test-token');
    });

    it('should handle network errors gracefully', async () => {
      mockFetch.mockRejectedValue(new Error('Network error'));

      const { default: api } = await import('@/lib/api');

      await expect(api.validateApiKey('groq', 'test')).rejects.toThrow('Network error');
    });
  });

  describe('Error Handling', () => {
    it('should handle 401 Unauthorized for getApiKeys', async () => {
      mockFetch.mockResolvedValue({
        ok: false,
        status: 401,
        statusText: 'Unauthorized',
        json: () => Promise.resolve({ error: 'Unauthorized' }),
        headers: new Headers({ 'content-type': 'application/json' }),
      });

      const { default: api } = await import('@/lib/api');

      await expect(api.getApiKeys()).rejects.toThrow();
    });

    it('should handle 500 Internal Server Error for updateApiKeys', async () => {
      mockFetch.mockResolvedValue({
        ok: false,
        status: 500,
        statusText: 'Internal Server Error',
        json: () => Promise.resolve({ error: 'Database connection failed' }),
        headers: new Headers({ 'content-type': 'application/json' }),
      });

      const { default: api } = await import('@/lib/api');

      await expect(api.updateApiKeys({ groq: 'test' })).rejects.toThrow();
    });

    it('should handle non-JSON response', async () => {
      mockFetch.mockResolvedValue({
        ok: true,
        status: 200,
        json: () => Promise.reject(new Error('Invalid JSON')),
        headers: new Headers({ 'content-type': 'text/plain' }),
      });

      const { default: api } = await import('@/lib/api');

      await expect(api.getApiKeys()).rejects.toThrow();
    });
  });
});
