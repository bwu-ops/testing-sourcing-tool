export type Maybe<T> = T | null;
export type InputMaybe<T> = Maybe<T>;
export type Exact<T extends { [key: string]: unknown }> = { [K in keyof T]: T[K] };
export type MakeOptional<T, K extends keyof T> = Omit<T, K> & { [SubKey in K]?: Maybe<T[SubKey]> };
export type MakeMaybe<T, K extends keyof T> = Omit<T, K> & { [SubKey in K]: Maybe<T[SubKey]> };
export type MakeEmpty<T extends { [key: string]: unknown }, K extends keyof T> = { [_ in K]?: never };
export type Incremental<T> = T | { [P in keyof T]?: P extends ' $fragmentName' | '__typename' ? T[P] : never };
/** All built-in and custom scalars, mapped to their actual values */
export type Scalars = {
  ID: { input: string; output: string; }
  String: { input: string; output: string; }
  Boolean: { input: boolean; output: boolean; }
  Int: { input: number; output: number; }
  Float: { input: number; output: number; }
};

export type ApproveSourcingCalibrationInput = {
  projectId: Scalars['String']['input'];
  scorecard: Array<Scalars['String']['input']>;
  targetCompanies: Array<Scalars['String']['input']>;
};

export type CandidateType = {
  __typename?: 'CandidateType';
  associatedProjectCount: Scalars['Int']['output'];
  currentCompany: Scalars['String']['output'];
  currentTitle: Scalars['String']['output'];
  fullName: Scalars['String']['output'];
  githubUrl: Scalars['String']['output'];
  id: Scalars['String']['output'];
  linkedinSlug: Scalars['String']['output'];
  linkedinUrl: Scalars['String']['output'];
  location: Scalars['String']['output'];
  locationConfidence: Scalars['String']['output'];
  sourceUrls: Array<Scalars['String']['output']>;
};

export type CreateNoteInput = {
  body?: Scalars['String']['input'];
  title: Scalars['String']['input'];
};

export type CreateSourcingProjectInput = {
  companyWebsite: Scalars['String']['input'];
  jobDescription: Scalars['String']['input'];
  notes?: Scalars['String']['input'];
};

export type CurrentUserType = {
  __typename?: 'CurrentUserType';
  email: Scalars['String']['output'];
  id: Scalars['String']['output'];
};

export type Mutation = {
  __typename?: 'Mutation';
  approveSourcingProjectCalibration: SourcingProjectType;
  createNote: NoteType;
  createSourcingProject: SourcingProjectType;
  runSourcingProjectSearch: SourcingProjectType;
  setSourcingCandidateFeedback: ProjectCandidateType;
  startNoteSummaryRun: TaskRunType;
  summarizeNote: NoteType;
};


export type MutationApproveSourcingProjectCalibrationArgs = {
  input: ApproveSourcingCalibrationInput;
};


export type MutationCreateNoteArgs = {
  input: CreateNoteInput;
};


export type MutationCreateSourcingProjectArgs = {
  input: CreateSourcingProjectInput;
};


export type MutationRunSourcingProjectSearchArgs = {
  projectId: Scalars['String']['input'];
};


export type MutationSetSourcingCandidateFeedbackArgs = {
  input: SetCandidateFeedbackInput;
};


export type MutationSummarizeNoteArgs = {
  noteId: Scalars['String']['input'];
};

export type NoteType = {
  __typename?: 'NoteType';
  body: Scalars['String']['output'];
  createdAt: Scalars['String']['output'];
  id: Scalars['String']['output'];
  summary?: Maybe<Scalars['String']['output']>;
  summaryProvider?: Maybe<Scalars['String']['output']>;
  summaryUpdatedAt?: Maybe<Scalars['String']['output']>;
  title: Scalars['String']['output'];
};

export type ProjectCandidateType = {
  __typename?: 'ProjectCandidateType';
  candidate: CandidateType;
  domainTags: Array<Scalars['String']['output']>;
  earlyStageSignal: Scalars['String']['output'];
  feedbackStatus?: Maybe<Scalars['String']['output']>;
  fitScore: Scalars['Int']['output'];
  id: Scalars['String']['output'];
  mustHaveScore: Scalars['String']['output'];
  rationale: Scalars['String']['output'];
  sourceConfidence: Scalars['String']['output'];
  targetCompanyMatch: Scalars['String']['output'];
};

export type Query = {
  __typename?: 'Query';
  candidates: Array<CandidateType>;
  currentUser: CurrentUserType;
  notes: Array<NoteType>;
  sourcingProject?: Maybe<SourcingProjectType>;
  sourcingProjects: Array<SourcingProjectType>;
  taskRun?: Maybe<TaskRunType>;
  taskRuns: Array<TaskRunType>;
  viewer: ViewerType;
};


export type QuerySourcingProjectArgs = {
  projectId: Scalars['String']['input'];
};


export type QueryTaskRunArgs = {
  taskRunId: Scalars['String']['input'];
};

export type SetCandidateFeedbackInput = {
  feedbackStatus: Scalars['String']['input'];
  projectCandidateId: Scalars['String']['input'];
};

export type SourcingProjectType = {
  __typename?: 'SourcingProjectType';
  approvedScorecard: Array<Scalars['String']['output']>;
  approvedTargetCompanies: Array<Scalars['String']['output']>;
  candidateArchetypes: Array<Scalars['String']['output']>;
  companyWebsite: Scalars['String']['output'];
  createdAt: Scalars['String']['output'];
  generatedScorecard: Array<Scalars['String']['output']>;
  generatedTargetCompanies: Array<Scalars['String']['output']>;
  id: Scalars['String']['output'];
  jobDescription: Scalars['String']['output'];
  name: Scalars['String']['output'];
  notes: Scalars['String']['output'];
  projectCandidates: Array<ProjectCandidateType>;
  searchKeywords: Array<Scalars['String']['output']>;
  status: Scalars['String']['output'];
  updatedAt: Scalars['String']['output'];
};

export type TaskRunType = {
  __typename?: 'TaskRunType';
  createdAt: Scalars['String']['output'];
  errorMessage?: Maybe<Scalars['String']['output']>;
  finishedAt?: Maybe<Scalars['String']['output']>;
  id: Scalars['String']['output'];
  message?: Maybe<Scalars['String']['output']>;
  progressCurrent: Scalars['Int']['output'];
  progressTotal: Scalars['Int']['output'];
  status: Scalars['String']['output'];
  taskName: Scalars['String']['output'];
  updatedAt: Scalars['String']['output'];
};

export type ViewerType = {
  __typename?: 'ViewerType';
  email: Scalars['String']['output'];
};
