// Printing uses the unmodified PDF, never HTML pagination or canvas snapshots.
export function printPdfBlob(encoded) {
  return new Blob([Uint8Array.from(atob(encoded), ch => ch.charCodeAt(0))], {
    type: 'application/pdf',
  });
}
