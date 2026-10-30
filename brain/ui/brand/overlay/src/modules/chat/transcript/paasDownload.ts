import { api, authenticatedFetch } from '@/shared/api';

/** Files Claude hands over (reports, spreadsheets, charts, archives): their chat links get a Download chip. */
export const PAAS_DOWNLOADABLE = /\.(xlsx|xlsm|xls|ods|odt|csv|tsv|pdf|png|jpe?g|gif|svg|html?|zip|gz|tgz|tar|docx|pptx|rtf|json|xml|ya?ml|txt|log|md|sql|conf|cfg|ini|sh|py|ps1)$/i;

/** Plain-words reason for a failed download. */
function failureText(name: string, status: number, statusText: string): string {
  if (status === 404) return `Could not download ${name}. It was moved or deleted. Ask Claude to create it again.`;
  if (status === 403) return 'Only files in your home folder or project can be downloaded.';
  return `Could not download ${name} (${statusText || status}). Try again.`;
}

/** A short status line next to the chip (no pop-up), read out by screen readers, gone after 6 s. */
function showNote(button: HTMLElement | undefined, text: string): void {
  if (!button) return;
  const note = document.createElement('span');
  note.setAttribute('role', 'status');
  note.className = 'paas-dl-note';
  note.textContent = text;
  button.insertAdjacentElement('afterend', note);
  setTimeout(() => note.remove(), 6000);
}

/**
 * Saves a file named in the chat to the browser's downloads: project-relative paths through the project files route,
 * absolute or ~ paths through /api/paas/download (home folder only, signed-in). The chip (`button`) is disabled and
 * marked busy while the file is fetched; a failure shows as a short line beside it.
 */
export async function downloadChatFile(reference: string, projectId: string | null, button?: HTMLButtonElement): Promise<void> {
  if (button?.disabled) return;
  const ref = reference.trim().replace(/:\d+(:\d+)?$/, '');
  const name = ref.split('/').pop() || 'download';
  if (button) { button.disabled = true; button.setAttribute('aria-busy', 'true'); }
  try {
    const response = /^(\/|~)/.test(ref) || !projectId
      ? await authenticatedFetch(`/api/paas/download?path=${encodeURIComponent(ref)}`)
      : await api.readFileBlob(projectId, ref);
    if (!response.ok) {
      showNote(button, failureText(name, response.status, response.statusText));
      return;
    }
    const url = URL.createObjectURL(await response.blob());
    const anchor = document.createElement('a');
    anchor.href = url;
    anchor.download = name;
    document.body.appendChild(anchor);
    anchor.click();
    anchor.remove();
    setTimeout(() => URL.revokeObjectURL(url), 60000);
  } catch {
    showNote(button, `Could not download ${name}. Check the connection and try again.`);
  } finally {
    if (button) { button.disabled = false; button.removeAttribute('aria-busy'); }
  }
}
