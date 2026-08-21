export async function requestRaw(url: string) {
  return safeHttp.axios.request({ url });
}
