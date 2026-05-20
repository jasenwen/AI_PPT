/**
 * PPT Engine API proxy routes.
 *
 * Proxies requests from the LibreChat frontend to the PPT Engine
 * microservice using axios (already a LibreChat dependency).
 * No additional npm packages required.
 */

const express = require('express');
const axios = require('axios');
const multer = require('multer');
const { requireJwtAuth } = require('~/server/middleware');

const router = express.Router();
router.use(requireJwtAuth);
const upload = multer({ storage: multer.memoryStorage(), limits: { fileSize: 100 * 1024 * 1024 } });

// PPT Engine base URL — configurable via environment variable
const PPT_ENGINE_URL = process.env.PPT_ENGINE_URL || 'http://localhost:8100';

/**
 * Generic proxy helper — forwards request to PPT Engine and pipes response back.
 */
async function proxyRequest(req, res, { method, path, data, headers = {}, responseType } = {}) {
  try {
    const url = `${PPT_ENGINE_URL}${path || req.originalUrl.replace(/^\/api\/ppt/, '/api')}`;
    const config = {
      method: method || req.method,
      url,
      headers: {
        ...headers,
        'x-user-id': req.user?.id || '',
      },
      timeout: 300000, // 5 minutes for long SVG generation
    };

    if (data) {
      config.data = data;
      config.headers['Content-Type'] = headers['Content-Type'] || 'application/json';
    } else if (['POST', 'PUT', 'PATCH'].includes(config.method.toUpperCase()) && req.body) {
      config.data = req.body;
      config.headers['Content-Type'] = req.get('Content-Type') || 'application/json';
    }

    if (responseType) {
      config.responseType = responseType;
    }

    const response = await axios(config);

    // Forward status and headers
    res.status(response.status);
    if (response.headers['content-type']) {
      res.set('Content-Type', response.headers['content-type']);
    }
    if (response.headers['content-disposition']) {
      res.set('Content-Disposition', response.headers['content-disposition']);
    }

    if (responseType === 'stream') {
      response.data.pipe(res);
    } else {
      res.json(response.data);
    }
  } catch (err) {
    const status = err.response?.status || 502;
    const message = err.response?.data || { error: 'PPT Engine unavailable', details: err.message };
    res.status(status).json(typeof message === 'string' ? { error: message } : message);
  }
}

// ---- Template management ----

router.get('/templates', (req, res) => proxyRequest(req, res));
router.get('/templates/:id', (req, res) => proxyRequest(req, res));
router.delete('/templates/:id', (req, res) => proxyRequest(req, res));
router.get('/templates/:id/pages/:filename', (req, res) =>
  proxyRequest(req, res, { responseType: 'stream' })
);

// Template upload — forward multipart form data
router.post('/templates/upload', upload.single('file'), async (req, res) => {
  try {
    const FormData = (await import('form-data')).default;
    const form = new FormData();

    if (req.file) {
      form.append('file', req.file.buffer, {
        filename: req.file.originalname,
        contentType: req.file.mimetype,
      });
    }
    // Forward other form fields
    for (const [key, value] of Object.entries(req.body || {})) {
      form.append(key, value);
    }

    const response = await axios.post(
      `${PPT_ENGINE_URL}/api/templates/upload`,
      form,
      {
        headers: {
          ...form.getHeaders(),
          'x-user-id': req.user?.id || '',
        },
        timeout: 120000,
      }
    );

    res.status(response.status).json(response.data);
  } catch (err) {
    const status = err.response?.status || 502;
    const message = err.response?.data || { error: 'Upload failed', details: err.message };
    res.status(status).json(typeof message === 'string' ? { error: message } : message);
  }
});

// ---- Document conversion ----
router.post('/convert', upload.single('file'), async (req, res) => {
  try {
    const FormData = (await import('form-data')).default;
    const form = new FormData();

    if (req.file) {
      form.append('file', req.file.buffer, {
        filename: req.file.originalname,
        contentType: req.file.mimetype,
      });
    }
    for (const [key, value] of Object.entries(req.body || {})) {
      form.append(key, value);
    }

    const response = await axios.post(
      `${PPT_ENGINE_URL}/api/convert`,
      form,
      {
        headers: {
          ...form.getHeaders(),
          'x-user-id': req.user?.id || '',
        },
        timeout: 60000,
      }
    );

    res.status(response.status).json(response.data);
  } catch (err) {
    const status = err.response?.status || 502;
    const message = err.response?.data || { error: 'Conversion failed', details: err.message };
    res.status(status).json(typeof message === 'string' ? { error: message } : message);
  }
});

// ---- Task lifecycle ----
router.post('/tasks', (req, res) => proxyRequest(req, res));
router.get('/tasks/:id', (req, res) => proxyRequest(req, res));
router.get('/tasks/:id/pages/:pageNum/svg', (req, res) =>
  proxyRequest(req, res, { responseType: 'stream' })
);
router.get('/tasks/:id/download', (req, res) =>
  proxyRequest(req, res, { responseType: 'stream' })
);

module.exports = router;
