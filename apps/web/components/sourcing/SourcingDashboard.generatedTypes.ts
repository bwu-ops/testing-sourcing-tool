import * as Types from '../../__generated_types__/globalTypes';

export type SourcingProjectFieldsForDashboardFragment = { __typename?: 'SourcingProjectType', id: string, name: string, status: string, jobDescription: string, companyWebsite: string, notes: string, generatedTargetCompanies: Array<string>, approvedTargetCompanies: Array<string>, generatedScorecard: Array<string>, approvedScorecard: Array<string>, searchKeywords: Array<string>, candidateArchetypes: Array<string>, createdAt: string, updatedAt: string, projectCandidates: Array<{ __typename?: 'ProjectCandidateType', id: string, fitScore: number, mustHaveScore: string, sourceConfidence: string, earlyStageSignal: string, rationale: string, domainTags: Array<string>, targetCompanyMatch: string, feedbackStatus?: string | null, candidate: { __typename?: 'CandidateType', id: string, fullName: string, linkedinUrl: string, linkedinSlug: string, currentTitle: string, currentCompany: string, location: string, locationConfidence: string, githubUrl: string, sourceUrls: Array<string>, associatedProjectCount: number } }> };

export type GetSourcingDashboardQueryVariables = Types.Exact<{ [key: string]: never; }>;


export type GetSourcingDashboardQuery = { __typename?: 'Query', sourcingProjects: Array<{ __typename?: 'SourcingProjectType', id: string, name: string, status: string, jobDescription: string, companyWebsite: string, notes: string, generatedTargetCompanies: Array<string>, approvedTargetCompanies: Array<string>, generatedScorecard: Array<string>, approvedScorecard: Array<string>, searchKeywords: Array<string>, candidateArchetypes: Array<string>, createdAt: string, updatedAt: string, projectCandidates: Array<{ __typename?: 'ProjectCandidateType', id: string, fitScore: number, mustHaveScore: string, sourceConfidence: string, earlyStageSignal: string, rationale: string, domainTags: Array<string>, targetCompanyMatch: string, feedbackStatus?: string | null, candidate: { __typename?: 'CandidateType', id: string, fullName: string, linkedinUrl: string, linkedinSlug: string, currentTitle: string, currentCompany: string, location: string, locationConfidence: string, githubUrl: string, sourceUrls: Array<string>, associatedProjectCount: number } }> }> };

export type CreateSourcingProjectFromDashboardMutationVariables = Types.Exact<{
  input: Types.CreateSourcingProjectInput;
}>;


export type CreateSourcingProjectFromDashboardMutation = { __typename?: 'Mutation', createSourcingProject: { __typename?: 'SourcingProjectType', id: string, name: string, status: string, jobDescription: string, companyWebsite: string, notes: string, generatedTargetCompanies: Array<string>, approvedTargetCompanies: Array<string>, generatedScorecard: Array<string>, approvedScorecard: Array<string>, searchKeywords: Array<string>, candidateArchetypes: Array<string>, createdAt: string, updatedAt: string, projectCandidates: Array<{ __typename?: 'ProjectCandidateType', id: string, fitScore: number, mustHaveScore: string, sourceConfidence: string, earlyStageSignal: string, rationale: string, domainTags: Array<string>, targetCompanyMatch: string, feedbackStatus?: string | null, candidate: { __typename?: 'CandidateType', id: string, fullName: string, linkedinUrl: string, linkedinSlug: string, currentTitle: string, currentCompany: string, location: string, locationConfidence: string, githubUrl: string, sourceUrls: Array<string>, associatedProjectCount: number } }> } };

export type ApproveSourcingProjectFromDashboardMutationVariables = Types.Exact<{
  input: Types.ApproveSourcingCalibrationInput;
}>;


export type ApproveSourcingProjectFromDashboardMutation = { __typename?: 'Mutation', approveSourcingProjectCalibration: { __typename?: 'SourcingProjectType', id: string, name: string, status: string, jobDescription: string, companyWebsite: string, notes: string, generatedTargetCompanies: Array<string>, approvedTargetCompanies: Array<string>, generatedScorecard: Array<string>, approvedScorecard: Array<string>, searchKeywords: Array<string>, candidateArchetypes: Array<string>, createdAt: string, updatedAt: string, projectCandidates: Array<{ __typename?: 'ProjectCandidateType', id: string, fitScore: number, mustHaveScore: string, sourceConfidence: string, earlyStageSignal: string, rationale: string, domainTags: Array<string>, targetCompanyMatch: string, feedbackStatus?: string | null, candidate: { __typename?: 'CandidateType', id: string, fullName: string, linkedinUrl: string, linkedinSlug: string, currentTitle: string, currentCompany: string, location: string, locationConfidence: string, githubUrl: string, sourceUrls: Array<string>, associatedProjectCount: number } }> } };

export type RunSourcingProjectSearchFromDashboardMutationVariables = Types.Exact<{
  projectId: Types.Scalars['String']['input'];
}>;


export type RunSourcingProjectSearchFromDashboardMutation = { __typename?: 'Mutation', runSourcingProjectSearch: { __typename?: 'SourcingProjectType', id: string, name: string, status: string, jobDescription: string, companyWebsite: string, notes: string, generatedTargetCompanies: Array<string>, approvedTargetCompanies: Array<string>, generatedScorecard: Array<string>, approvedScorecard: Array<string>, searchKeywords: Array<string>, candidateArchetypes: Array<string>, createdAt: string, updatedAt: string, projectCandidates: Array<{ __typename?: 'ProjectCandidateType', id: string, fitScore: number, mustHaveScore: string, sourceConfidence: string, earlyStageSignal: string, rationale: string, domainTags: Array<string>, targetCompanyMatch: string, feedbackStatus?: string | null, candidate: { __typename?: 'CandidateType', id: string, fullName: string, linkedinUrl: string, linkedinSlug: string, currentTitle: string, currentCompany: string, location: string, locationConfidence: string, githubUrl: string, sourceUrls: Array<string>, associatedProjectCount: number } }> } };

export type SetSourcingCandidateFeedbackFromDashboardMutationVariables = Types.Exact<{
  input: Types.SetCandidateFeedbackInput;
}>;


export type SetSourcingCandidateFeedbackFromDashboardMutation = { __typename?: 'Mutation', setSourcingCandidateFeedback: { __typename?: 'ProjectCandidateType', id: string, feedbackStatus?: string | null } };
