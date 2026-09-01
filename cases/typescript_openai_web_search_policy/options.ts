export const importedSearchOptions = {
  filters: {
    allowedDomains: ["kb.example.com", "support.example.com"],
  },
  searchContextSize: "medium",
};

export const mutableImportedSearchOptions = {
  filters: {
    allowedDomains: ["mutable-import.example.com"],
  },
};
mutableImportedSearchOptions.filters.allowedDomains = [];
