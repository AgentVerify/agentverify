import { ssrfSafeFetch, ssrfSafeFetchWhereSupported } from '#ssrf_guard';

export class ToolRouterSessionFilesMount {
  private async normalizeUploadInput(input: string) {
    return ssrfSafeFetch(input);
  }

  async upload(input: string, uploadURLData: unknown) {
    await this.normalizeUploadInput(input);
    return ssrfSafeFetchWhereSupported(
      (uploadURLData as { upload_url: string }).upload_url,
      { method: 'PUT' },
    );
  }
}
