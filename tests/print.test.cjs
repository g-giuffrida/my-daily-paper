const {test} = require('node:test');
const assert = require('node:assert/strict');
const {readFileSync} = require('node:fs');
const {join} = require('node:path');

test('print blob preserves every byte of the original PDF', async () => {
  const {printPdfBlob} = await import('../components/viewer/print.mjs');
  const original = Buffer.from('%PDF-1.4\n' + String.fromCharCode(0, 127, 128, 255), 'latin1');
  const blob = printPdfBlob(original.toString('base64'));
  assert.equal(blob.type, 'application/pdf');
  assert.deepEqual(Buffer.from(await blob.arrayBuffer()), original);
});

test('print route cannot repaginate the PDF as a web page', () => {
  const viewer = readFileSync(join(__dirname, '../components/viewer/index.html'), 'utf8');
  assert.match(viewer, /doc.numPages!==2/);
  assert.match(viewer, /window.open\(printUrl,'_blank'\)/);
  assert.doesNotMatch(viewer, /\.print\(|toDataURL|d.write|@media print|print-sheets/);
});
