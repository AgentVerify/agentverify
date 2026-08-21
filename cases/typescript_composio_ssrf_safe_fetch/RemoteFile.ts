import { ssrfSafeFetchWhereSupported } from '#ssrf_guard';

export class RemoteFile {
  constructor(readonly downloadUrl: string) {}

  async buffer() {
    return ssrfSafeFetchWhereSupported(this.downloadUrl);
  }

  async blob() {
    return ssrfSafeFetchWhereSupported(this.downloadUrl);
  }
}
