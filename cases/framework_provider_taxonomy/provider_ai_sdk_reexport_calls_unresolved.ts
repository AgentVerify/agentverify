import { ambiguousProvider } from './provider_ai_sdk_reexports_ambiguous';
import { projectAzureFactory, projectOpenAI } from './provider_ai_sdk_reexports';

const ambiguousModel = ambiguousProvider('gpt-ambiguous-reexport');

function shadowed(projectOpenAI: (model: string) => unknown) {
  return projectOpenAI('gpt-shadowed-reexport');
}

const unsafeAzure = projectAzureFactory({
  resourceName: 'agentverify-resource',
  apiKey: process.env.AZURE_API_KEY,
  ...spreadIfDefined('baseURL', process.env.AZURE_BASE_URL),
});
const unsafeAzureModel = unsafeAzure('azure-reexport-custom-endpoint');

void ambiguousModel;
void shadowed;
void unsafeAzureModel;
