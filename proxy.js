// Simple HTTP proxy for /api requests - bypasses Vite's broken proxy
const http = require('http');

const BACKEND = { host: '127.0.0.1', port: 8000 };
const VITE = { host: '127.0.0.1', port: 5174 };  // Vite on internal port
const PROXY_PORT = 5173;  // Proxy on the externally accessible port

let reqCount = 0;
const server = http.createServer((clientReq, clientRes) => {
  const id = ++reqCount;
  // Test endpoint - returns JSON directly, no proxy
  if (clientReq.url === '/api/_proxy_test' || clientReq.url === '/_test' || clientReq.url === '/data/_test' || clientReq.url === '/backend/_test' || clientReq.url === '/d/_test') {
    const body = JSON.stringify({status: 'ok', source: 'proxy-direct', time: Date.now()});
    clientRes.writeHead(200, {
      'Content-Type': 'application/json',
      'Content-Length': Buffer.byteLength(body),
      'Access-Control-Allow-Origin': '*',
    });
    clientRes.end(body);
    console.log(`[${id}] DIRECT TEST -> 200`);
    return;
  }

  // Route /d/ requests to backend (rewriting to /api/ for FastAPI)
  const isApi = clientReq.url.startsWith('/d/');
  if (isApi) {
    // Rewrite /d/ -> /api/ for the backend
    clientReq.url = '/api/' + clientReq.url.slice(3);
  }
  const target = isApi ? BACKEND : VITE;

  if (isApi) {
    console.log(`[${id}] -> ${clientReq.method} ${clientReq.url} (from ${clientReq.socket.remoteAddress})`);
  }

  const options = {
    hostname: target.host,
    port: target.port,
    path: clientReq.url,
    method: clientReq.method,
    headers: { ...clientReq.headers, host: `${target.host}:${target.port}` },
  };

  const proxyReq = http.request(options, (proxyRes) => {
    if (isApi) {
      console.log(`[${id}] <- ${proxyRes.statusCode} ${clientReq.url}`);
    }
    clientRes.writeHead(proxyRes.statusCode, proxyRes.headers);
    proxyRes.pipe(clientRes, { end: true });
  });

  proxyReq.on('error', (err) => {
    console.error(`[${id}] ERROR for ${clientReq.url}:`, err.message);
    clientRes.writeHead(502);
    clientRes.end('Bad Gateway');
  });

  clientReq.pipe(proxyReq, { end: true });
});

// Also handle WebSocket upgrades (for Vite HMR)
server.on('upgrade', (req, socket, head) => {
  const options = {
    hostname: VITE.host,
    port: VITE.port,
    path: req.url,
    method: req.method,
    headers: { ...req.headers, host: `${VITE.host}:${VITE.port}` },
  };

  const proxyReq = http.request(options);
  proxyReq.on('upgrade', (proxyRes, proxySocket, proxyHead) => {
    socket.write(
      `HTTP/1.1 101 ${proxyRes.statusMessage}\r\n` +
      Object.entries(proxyRes.headers).map(([k,v]) => `${k}: ${v}`).join('\r\n') +
      '\r\n\r\n'
    );
    if (proxyHead.length) socket.write(proxyHead);
    proxySocket.pipe(socket);
    socket.pipe(proxySocket);
  });
  proxyReq.on('error', (err) => {
    console.error('WS proxy error:', err.message);
    socket.destroy();
  });
  proxyReq.end();
});

server.listen(PROXY_PORT, '0.0.0.0', () => {
  console.log(`Proxy listening on port ${PROXY_PORT}`);
  console.log(`  /api/* -> ${BACKEND.host}:${BACKEND.port}`);
  console.log(`  /*     -> ${VITE.host}:${VITE.port}`);
});
