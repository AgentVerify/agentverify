function requestDomainApproval(_domain: string, _url: string) {
  return true;
}

const webFetchSchema = { parse: (input: unknown) => input as { url: string } };

async function fetchUrl(_url: string, _ssrf: object) {
  return { finalUrl: "https://example.test" };
}

export function createWebFetchTool(createSecurity: () => object, ssrf: any) {
  return async function run(input: unknown) {
    createSecurity();
    const validatedInput = webFetchSchema.parse(input);
    const { url } = validatedInput;
    await ssrf.validateUrl(url);
    requestDomainApproval(new URL(url).hostname, url);
    const fetchResult = await fetchUrl(url, ssrf);
    await ssrf.validateUrl(fetchResult.finalUrl);
    return await fetchUrl(fetchResult.finalUrl, ssrf);
  };
}
