import axios, { AxiosInstance, AxiosRequestConfig } from "axios";
import {
  RequestFilteringHttpAgent,
  RequestFilteringHttpsAgent,
} from "request-filtering-agent";

function parseAllowListFromEnv(): string[] {
  const raw = process.env['AP_SSRF_ALLOW_LIST'];
  if (!raw) return [];
  return raw.split(',').map((s) => s.trim()).filter(Boolean);
}

function buildAgents({ allowList, httpsAgentOptions }: any) {
  const filteringOptions = {
    keepAlive: true,
    allowPrivateIPAddress: false,
    allowLoopbackIPAddress: false,
    allowMetaIPAddress: false,
    allowIPAddressList: allowList,
  };
  return {
    httpAgent: new RequestFilteringHttpAgent(filteringOptions),
    httpsAgent: new RequestFilteringHttpsAgent({ ...filteringOptions, ...httpsAgentOptions }),
  };
}

function attachSsrfErrorInterceptor(instance: AxiosInstance): AxiosInstance {
  return instance;
}

function createAxios(config?: AxiosRequestConfig, { httpsAgentOptions }: any = {}): AxiosInstance {
  const { httpAgent, httpsAgent } = buildAgents({
    allowList: parseAllowListFromEnv(),
    httpsAgentOptions,
  });
  return attachSsrfErrorInterceptor(axios.create({
    ...config,
    httpAgent,
    httpsAgent,
  }));
}

let lazyDefaultAxios: AxiosInstance | undefined;

export const safeHttp = {
  buildAgents,
  createAxios,
  get axios(): AxiosInstance {
    lazyDefaultAxios ??= createAxios();
    return lazyDefaultAxios;
  },
};
