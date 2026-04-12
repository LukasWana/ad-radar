const https = require('https');
const http = require('http');

function fetch(url) {
  return new Promise((resolve, reject) => {
    const protocol = url.startsWith('https') ? https : http;
    const req = protocol.get(url, { 
      headers: { 'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36' },
      timeout: 15000
    }, res => {
      let data = '';
      res.on('data', chunk => data += chunk);
      res.on('end', () => resolve({status: res.statusCode, data}));
    });
    req.on('error', reject);
    req.on('timeout', () => reject(new Error('Timeout')));
  });
}

async function testSources() {
  const sources = [
    'https://www.adsoftheworld.com/',
    'https://www.canneslions.com/',
    'https://www.d-ad.com/'
  ];
  
  for (const url of sources) {
    try {
      console.log(`Testing: ${url}`);
      const result = await fetch(url);
      console.log(`  Status: ${result.status}, Length: ${result.data.length}`);
    } catch(e) {
      console.log(`  Failed: ${e.message}`);
    }
  }
}

testSources().catch(console.error);