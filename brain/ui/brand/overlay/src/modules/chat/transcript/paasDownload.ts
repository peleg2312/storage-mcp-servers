import { api, authenticatedFetch } from '@/shared/api';

/** Files Claude hands over (reports, spreadsheets, charts, archives): their chat links get a Download chip. */
export const PAAS_DOWNLOADABLE = /\.(xlsx|xls|csv|pdf|png|jpe?g|gif|svg|html?|zip|gz|tgz|tar|docx|pptx|json|txt|log)$/i;

/**
 * Saves a file named in the chat to the browser's downloads: project-relative paths through the project files route,
 * absolute or ~ paths through /api/paas/download (home folder only, signed-in).
 */
export async function downloadChatFile(reference: string, projectId: string | null): Promise<void> {
  const ref = reference.trim().replace(/:\d+(:\d+)?$/, '');
  const response = /^(\/|~)/.test(ref) || !projectId
    ? await authenticatedFetch(`/api/paas/download?path=${encodeURIComponent(ref)}`)
    : await api.readFileBlob(projectId, ref);
  if (!response.ok) {
    const message = await response.json().then((d: { error?: string }) => d.error).catch(() => null);
    window.alert(`Could not download ${ref}: ${message || response.statusText}`);
    return;
  }
  const url = URL.createObjectURL(await response.blob());
  const anchor = document.createElement('a');
  anchor.href = url;
  anchor.download = ref.split('/').pop() || 'download';
  document.body.appendChild(anchor);
  anchor.click();
  anchor.remove();
  setTimeout(() => URL.revokeObjectURL(url), 60000);
}
