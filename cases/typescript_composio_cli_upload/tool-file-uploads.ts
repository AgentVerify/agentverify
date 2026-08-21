const readFileFromUrl = async (path: unknown, url: string) => {
  const response = await fetch(url);
  return { path, response };
};

const readUploadSource = async (fs: unknown, path: unknown, file: unknown) => {
  if (typeof file === 'string' && /^https?:\/\//i.test(file)) {
    return readFileFromUrl(path, file);
  }
  return file;
};

const uploadFile = async (params: { fs: unknown; path: unknown; file: unknown }) =>
  readUploadSource(params.fs, params.path, params.file);

const hydrateFileUploads = async (value: unknown, schema: { file_uploadable?: boolean }) => {
  if (schema?.file_uploadable === true) {
    return uploadFile({ fs: {}, path: {}, file: value });
  }
  return value;
};

export const uploadToolInputFiles = async (params: {
  arguments_: Record<string, unknown>;
  inputSchema: { file_uploadable?: boolean };
}) => hydrateFileUploads(params.arguments_, params.inputSchema);
