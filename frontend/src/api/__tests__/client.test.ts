import { extractData, extractError } from '../client';

describe('api client utils', () => {
  test('extractData возвращает data при success=true', () => {
    const response = {
      data: {
        success: true,
        data: { id: '123', name: 'Test' },
      },
    };
    expect(extractData(response)).toEqual({ id: '123', name: 'Test' });
  });

  test('extractData выбрасывает ошибку при success=false', () => {
    const response = {
      data: {
        success: false,
        data: null,
      },
    };
    expect(() => extractData(response)).toThrow('API вернул success: false');
  });

  test('extractError возвращает ошибку из response.data.error', () => {
    const error = {
      response: {
        data: {
          error: {
            code: 'NOT_FOUND',
            message: 'Сущность не найдена',
            details: { id: '123' },
          },
        },
      },
    };
    expect(extractError(error)).toEqual({
      code: 'NOT_FOUND',
      message: 'Сущность не найдена',
      details: { id: '123' },
    });
  });

  test('extractError возвращает UNKNOWN_ERROR при отсутствии response', () => {
    const error = { message: 'Network Error' };
    const result = extractError(error);
    expect(result.code).toBe('UNKNOWN_ERROR');
    expect(result.message).toBe('Network Error');
  });
});