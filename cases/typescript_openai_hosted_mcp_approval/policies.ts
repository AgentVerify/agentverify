export const importedPolicy = {
  never: { toolNames: ["read_imported"], readOnly: true },
  always: { toolNames: ["write_imported"] },
};

export const aliasedPolicy = {
  never: { toolNames: ["list_imported"] },
  always: { toolNames: ["delete_imported"] },
};

export const mutatedExport = {
  never: { toolNames: ["read_mutated"] },
  always: { toolNames: ["write_mutated"] },
};
mutatedExport.always = { toolNames: ["delete_mutated"] };
