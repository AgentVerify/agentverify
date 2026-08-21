import { uploadToolInputFiles } from 'src/services/tool-file-uploads';

export interface ToolsExecutor {
  execute(slug: string, params: { arguments: Record<string, unknown> }): unknown;
}

export const ToolsExecutor = {
  execute: (slug, params) => {
    const definition = { schema: { file_uploadable: true } };
    return uploadToolInputFiles({
      arguments_: params.arguments,
      inputSchema: definition.schema,
    });
  },
};
