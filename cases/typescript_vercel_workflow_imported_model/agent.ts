import { WorkflowAgent } from "@ai-sdk/workflow";
import { workflowModel, castModel, mutableModel } from "./models";
import { workflowModel as namedReexportModel } from "./barrel";
import { workflowModel as starReexportModel } from "./star-barrel";
import { ambiguousModel } from "./ambiguous-barrel";

const directImportedAgent = new WorkflowAgent({ model: workflowModel });
const namedReexportAgent = new WorkflowAgent({ model: namedReexportModel });
const starReexportAgent = new WorkflowAgent({ model: starReexportModel });
const castAgent = new WorkflowAgent({ model: castModel });
const mutableAgent = new WorkflowAgent({ model: mutableModel });
const ambiguousAgent = new WorkflowAgent({ model: ambiguousModel });

void directImportedAgent;
void namedReexportAgent;
void starReexportAgent;
void castAgent;
void mutableAgent;
void ambiguousAgent;
