type Readable = object;
const axios = { get: async <T>(_url: string, _config: object): Promise<T> => ({}) as T };
const WEB_FETCH_MAX_REDIRECTS = 5;

export async function fetchUrl(url: string, ssrf: any) {
  await ssrf.validateUrl(url);
  const config = {
    lookup: ssrf.createSecureLookup(),
    beforeRedirect: (opts: { href: string }) => {
      ssrf.validateRedirectSync(opts.href);
    },
    maxRedirects: WEB_FETCH_MAX_REDIRECTS,
  };
  return await axios.get<Readable>(url, config);
}
