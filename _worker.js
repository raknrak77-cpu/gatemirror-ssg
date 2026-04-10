export default {
  async fetch(request, env, ctx) {
    const R2_BASE = 'https://pub-f9790eb09fb8460a9ba4e1509db5b135.r2.dev';
    const url = new URL(request.url);
    let path = url.pathname;

    // Kök dizine gelen istekleri ana sayfaya yönlendir
    if (path === '/' || path === '') {
      path = '/articles/en/index.html';
    }

    const r2Url = `${R2_BASE}${path}`;
    
    try {
      const response = await fetch(r2Url);
      
      if (!response.ok) {
        // 404 durumunda ana sayfaya yönlendir
        if (response.status === 404) {
          const fallbackUrl = `${R2_BASE}/articles/en/index.html`;
          return fetch(fallbackUrl);
        }
        return new Response('Not found', { status: 404 });
      }
      
      // CORS header'larını ekle (isteğe bağlı)
      const headers = new Headers(response.headers);
      headers.set('Access-Control-Allow-Origin', '*');
      
      return new Response(response.body, {
        status: response.status,
        headers: headers
      });
    } catch (error) {
      return new Response('Error fetching from R2', { status: 500 });
    }
  }
};
