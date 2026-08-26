import { ambiguousProvider } from './provider_ai_sdk_reexports_ambiguous';
import { projectOpenAI } from './provider_ai_sdk_reexports';

const ambiguousModel = ambiguousProvider('gpt-ambiguous-reexport');

function shadowed(projectOpenAI: (model: string) => unknown) {
  return projectOpenAI('gpt-shadowed-reexport');
}

void ambiguousModel;
void shadowed;
