import { gql } from '@apollo/client'
import { useMutation, useQuery } from '@apollo/client/react'
import { type FormEvent, useEffect, useMemo, useState } from 'react'
import { useRouter } from 'next/router'

import { Button } from '@/components/generic/Button'
import { Input } from '@/components/generic/Input'
import SectionContainer from '@/components/generic/SectionContainer'
import { Spinner } from '@/components/generic/Spinner'
import { Textarea } from '@/components/generic/Textarea'
import useCurrentUser from '@/hooks/useCurrentUser'
import { getErrorMessage } from '@/lib/getErrorMessage'
import { isUnauthorizedApolloError } from '@/lib/isUnauthorizedApolloError'
import { requestApiJson } from '@/lib/requestApiJson'

import {
  ApproveSourcingProjectFromDashboardMutation,
  ApproveSourcingProjectFromDashboardMutationVariables,
  CreateSourcingProjectFromDashboardMutation,
  CreateSourcingProjectFromDashboardMutationVariables,
  GetSourcingDashboardQuery,
  GetSourcingDashboardQueryVariables,
  RunSourcingProjectSearchFromDashboardMutation,
  RunSourcingProjectSearchFromDashboardMutationVariables,
  SetSourcingCandidateFeedbackFromDashboardMutation,
  SetSourcingCandidateFeedbackFromDashboardMutationVariables,
} from './SourcingDashboard.generatedTypes'

const SOURCING_PROJECT_FIELDS = gql`
  fragment SourcingProjectFieldsForDashboard on SourcingProjectType {
    id
    name
    status
    jobDescription
    companyWebsite
    notes
    generatedTargetCompanies
    approvedTargetCompanies
    generatedScorecard
    approvedScorecard
    searchKeywords
    candidateArchetypes
    createdAt
    updatedAt
    projectCandidates {
      id
      fitScore
      mustHaveScore
      sourceConfidence
      earlyStageSignal
      rationale
      domainTags
      targetCompanyMatch
      feedbackStatus
      candidate {
        id
        fullName
        linkedinUrl
        linkedinSlug
        currentTitle
        currentCompany
        location
        locationConfidence
        githubUrl
        sourceUrls
        associatedProjectCount
      }
    }
  }
`

const GET_SOURCING_DASHBOARD = gql`
  query GetSourcingDashboard {
    sourcingProjects {
      ...SourcingProjectFieldsForDashboard
    }
  }
  ${SOURCING_PROJECT_FIELDS}
`

const CREATE_SOURCING_PROJECT = gql`
  mutation CreateSourcingProjectFromDashboard($input: CreateSourcingProjectInput!) {
    createSourcingProject(input: $input) {
      ...SourcingProjectFieldsForDashboard
    }
  }
  ${SOURCING_PROJECT_FIELDS}
`

const APPROVE_SOURCING_PROJECT = gql`
  mutation ApproveSourcingProjectFromDashboard(
    $input: ApproveSourcingCalibrationInput!
  ) {
    approveSourcingProjectCalibration(input: $input) {
      ...SourcingProjectFieldsForDashboard
    }
  }
  ${SOURCING_PROJECT_FIELDS}
`

const RUN_SOURCING_PROJECT_SEARCH = gql`
  mutation RunSourcingProjectSearchFromDashboard($projectId: String!) {
    runSourcingProjectSearch(projectId: $projectId) {
      ...SourcingProjectFieldsForDashboard
    }
  }
  ${SOURCING_PROJECT_FIELDS}
`

const SET_SOURCING_CANDIDATE_FEEDBACK = gql`
  mutation SetSourcingCandidateFeedbackFromDashboard(
    $input: SetCandidateFeedbackInput!
  ) {
    setSourcingCandidateFeedback(input: $input) {
      id
      feedbackStatus
    }
  }
`

type Project = GetSourcingDashboardQuery['sourcingProjects'][number]
type ProjectCandidate = Project['projectCandidates'][number]

const splitLines = (value: string) =>
  value
    .split('\n')
    .map((item) => item.trim())
    .filter(Boolean)

const csvEscape = (value: string | number | null | undefined) => {
  const text = String(value ?? '')
  if (!/[",\n]/.test(text)) {
    return text
  }
  return `"${text.replace(/"/g, '""')}"`
}

const downloadCsv = (project: Project) => {
  const headers = [
    'First name',
    'Last name',
    'Full name',
    'LinkedIn URL',
    'Current title',
    'Current company',
    'Location',
    'Location confidence',
    'Past companies',
    'Must-have score',
    'Fit score',
    'Source confidence',
    'Early-stage signal',
    'Candidate rationale',
    'GitHub URL',
    'Source URLs',
    'Project name',
    'Export date',
  ]
  const rows = project.projectCandidates.map((projectCandidate) => {
    const candidate = projectCandidate.candidate
    const [firstName, ...lastNameParts] = candidate.fullName.split(' ')
    return [
      firstName,
      lastNameParts.join(' '),
      candidate.fullName,
      candidate.linkedinUrl,
      candidate.currentTitle,
      candidate.currentCompany,
      candidate.location,
      candidate.locationConfidence,
      '',
      projectCandidate.mustHaveScore,
      projectCandidate.fitScore,
      projectCandidate.sourceConfidence,
      projectCandidate.earlyStageSignal,
      projectCandidate.rationale,
      candidate.githubUrl,
      candidate.sourceUrls.join(' '),
      project.name,
      new Date().toISOString(),
    ]
  })
  const csv = [headers, ...rows]
    .map((row) => row.map((value) => csvEscape(value)).join(','))
    .join('\n')
  const blob = new Blob([csv], { type: 'text/csv;charset=utf-8' })
  const url = URL.createObjectURL(blob)
  const link = document.createElement('a')
  link.href = url
  link.download = `${project.name.replace(/[^a-z0-9]+/gi, '-').toLowerCase()}-candidates.csv`
  link.click()
  URL.revokeObjectURL(url)
}

const statusLabel = (status: string) => status.replace(/_/g, ' ')

const SourcingDashboard = () => {
  const router = useRouter()
  const [jobDescription, setJobDescription] = useState('')
  const [companyWebsite, setCompanyWebsite] = useState('')
  const [notes, setNotes] = useState('')
  const [selectedProjectId, setSelectedProjectId] = useState<string | null>(null)
  const [draftCalibrationProjectId, setDraftCalibrationProjectId] = useState<
    string | null
  >(null)
  const [targetCompaniesText, setTargetCompaniesText] = useState('')
  const [scorecardText, setScorecardText] = useState('')
  const [errorMessage, setErrorMessage] = useState<string | null>(null)

  const {
    currentUser,
    error: currentUserError,
    isUnauthorized,
    loading: currentUserLoading,
  } = useCurrentUser()

  const {
    data,
    error: projectsError,
    loading: projectsLoading,
    refetch,
  } = useQuery<GetSourcingDashboardQuery, GetSourcingDashboardQueryVariables>(
    GET_SOURCING_DASHBOARD,
    { skip: !currentUser }
  )

  const [createSourcingProject, { loading: creatingProject }] = useMutation<
    CreateSourcingProjectFromDashboardMutation,
    CreateSourcingProjectFromDashboardMutationVariables
  >(CREATE_SOURCING_PROJECT)
  const [approveSourcingProject, { loading: approvingProject }] = useMutation<
    ApproveSourcingProjectFromDashboardMutation,
    ApproveSourcingProjectFromDashboardMutationVariables
  >(APPROVE_SOURCING_PROJECT)
  const [runSourcingProjectSearch, { loading: runningSearch }] = useMutation<
    RunSourcingProjectSearchFromDashboardMutation,
    RunSourcingProjectSearchFromDashboardMutationVariables
  >(RUN_SOURCING_PROJECT_SEARCH)
  const [setSourcingCandidateFeedback] = useMutation<
    SetSourcingCandidateFeedbackFromDashboardMutation,
    SetSourcingCandidateFeedbackFromDashboardMutationVariables
  >(SET_SOURCING_CANDIDATE_FEEDBACK)

  const projects = useMemo(() => data?.sourcingProjects ?? [], [data?.sourcingProjects])
  const selectedProject = useMemo(
    () =>
      projects.find((project) => project.id === selectedProjectId) ??
      projects[0] ??
      null,
    [projects, selectedProjectId]
  )
  const defaultTargetCompaniesText = useMemo(() => {
    if (!selectedProject) {
      return ''
    }
    return (
      selectedProject.approvedTargetCompanies.length > 0
        ? selectedProject.approvedTargetCompanies
        : selectedProject.generatedTargetCompanies
    ).join('\n')
  }, [selectedProject])
  const defaultScorecardText = useMemo(() => {
    if (!selectedProject) {
      return ''
    }
    return (
      selectedProject.approvedScorecard.length > 0
        ? selectedProject.approvedScorecard
        : selectedProject.generatedScorecard
    ).join('\n')
  }, [selectedProject])
  const editableTargetCompaniesText =
    draftCalibrationProjectId === selectedProject?.id
      ? targetCompaniesText
      : defaultTargetCompaniesText
  const editableScorecardText =
    draftCalibrationProjectId === selectedProject?.id
      ? scorecardText
      : defaultScorecardText

  const shouldRedirectToLogin =
    isUnauthorized || (!currentUserLoading && !currentUser && !currentUserError)

  useEffect(() => {
    if (shouldRedirectToLogin) {
      void router.replace('/login')
    }
  }, [router, shouldRedirectToLogin])

  const handleCreateProject = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault()
    setErrorMessage(null)
    try {
      const result = await createSourcingProject({
        variables: {
          input: { jobDescription, companyWebsite, notes },
        },
      })
      const project = result.data?.createSourcingProject
      if (project) {
        setSelectedProjectId(project.id)
        setDraftCalibrationProjectId(null)
      }
      setJobDescription('')
      setCompanyWebsite('')
      setNotes('')
      await refetch()
    } catch (err) {
      if (isUnauthorizedApolloError(err)) {
        await router.push('/login')
        return
      }
      setErrorMessage(getErrorMessage(err))
    }
  }

  const logout = async () => {
    setErrorMessage(null)
    try {
      await requestApiJson('/api/auth/logout', { method: 'POST' })
      await router.push('/login')
    } catch (err) {
      setErrorMessage(getErrorMessage(err))
    }
  }

  const handleApprove = async () => {
    if (!selectedProject) {
      return
    }
    setErrorMessage(null)
    try {
      await approveSourcingProject({
        variables: {
          input: {
            projectId: selectedProject.id,
            targetCompanies: splitLines(editableTargetCompaniesText),
            scorecard: splitLines(editableScorecardText),
          },
        },
      })
      await refetch()
    } catch (err) {
      setErrorMessage(getErrorMessage(err))
    }
  }

  const handleRunSearch = async () => {
    if (!selectedProject) {
      return
    }
    setErrorMessage(null)
    try {
      await runSourcingProjectSearch({ variables: { projectId: selectedProject.id } })
      await refetch()
    } catch (err) {
      setErrorMessage(getErrorMessage(err))
    }
  }

  const handleFeedback = async (
    projectCandidate: ProjectCandidate,
    feedbackStatus: string
  ) => {
    setErrorMessage(null)
    try {
      await setSourcingCandidateFeedback({
        variables: {
          input: {
            projectCandidateId: projectCandidate.id,
            feedbackStatus,
          },
        },
      })
      await refetch()
    } catch (err) {
      setErrorMessage(getErrorMessage(err))
    }
  }

  const visibleErrorMessage =
    errorMessage ||
    (!isUnauthorized && currentUserError ? getErrorMessage(currentUserError) : null) ||
    (projectsError ? getErrorMessage(projectsError) : null)

  if (currentUserLoading || shouldRedirectToLogin) {
    return (
      <div className="flex h-screen w-full items-center justify-center">
        <Spinner className="text-blue-400 text-2xl" />
      </div>
    )
  }

  if (!currentUser) {
    return null
  }

  return (
    <div className="mx-auto flex min-h-screen w-full max-w-7xl flex-col gap-5 p-6">
      <div className="flex flex-col gap-3 md:flex-row md:items-center md:justify-between">
        <div>
          <h1 className="text-2xl font-semibold text-primary-foreground">
            Talent mapping prototype
          </h1>
          <p className="mt-1 text-sm text-secondary-foreground">
            Build calibrated NYC software engineer maps with LinkedIn-backed candidates.
          </p>
        </div>
        <div className="flex flex-col items-start gap-2 text-sm text-secondary-foreground md:items-end">
          <span>Signed in as {currentUser.email}</span>
          <Button onClick={() => void logout()} type="button" variant="outline">
            Logout
          </Button>
        </div>
      </div>

      <div className="grid gap-5 lg:grid-cols-[420px_1fr]">
        <div className="flex flex-col gap-5">
          <SectionContainer title="New project" titleClassName="text-base">
            <form className="mt-4 flex flex-col gap-3" onSubmit={handleCreateProject}>
              <Textarea
                required
                placeholder="Paste the portfolio company job description..."
                rows={8}
                value={jobDescription}
                onChange={(event) => setJobDescription(event.target.value)}
              />
              <Input
                required
                placeholder="https://company.com"
                value={companyWebsite}
                onChange={(event) => setCompanyWebsite(event.target.value)}
              />
              <Textarea
                placeholder="Optional notes, e.g. prioritize stablecoin infrastructure"
                rows={3}
                value={notes}
                onChange={(event) => setNotes(event.target.value)}
              />
              <Button disabled={creatingProject} type="submit">
                {creatingProject ? 'Generating...' : 'Generate calibration'}
              </Button>
            </form>
          </SectionContainer>

          <SectionContainer title="Saved projects" titleClassName="text-base">
            <div className="mt-4 flex flex-col gap-2">
              {projectsLoading ? (
                <div className="text-sm text-secondary-foreground">
                  Loading projects...
                </div>
              ) : null}
              {!projectsLoading && projects.length === 0 ? (
                <div className="text-sm text-secondary-foreground">
                  No sourcing projects yet.
                </div>
              ) : null}
              {projects.map((project) => (
                <button
                  className={`rounded-md border p-3 text-left text-sm transition-colors ${
                    selectedProject?.id === project.id
                      ? 'border-blue-400 bg-blue-900'
                      : 'border-neutral-750 bg-neutral-850 hover:border-neutral-700'
                  }`}
                  key={project.id}
                  onClick={() => {
                    setSelectedProjectId(project.id)
                    setDraftCalibrationProjectId(null)
                  }}
                  type="button"
                >
                  <div className="font-medium text-primary-foreground">
                    {project.name}
                  </div>
                  <div className="mt-1 text-xs text-secondary-foreground">
                    {statusLabel(project.status)} · {project.projectCandidates.length}{' '}
                    candidates
                  </div>
                </button>
              ))}
            </div>
          </SectionContainer>
        </div>

        <div className="flex flex-col gap-5">
          {selectedProject ? (
            <>
              <SectionContainer title="Calibration" titleClassName="text-base">
                <div className="mt-4 grid gap-4 md:grid-cols-2">
                  <label className="flex flex-col gap-2 text-sm">
                    <span className="font-medium text-primary-foreground">
                      Target companies
                    </span>
                    <Textarea
                      rows={10}
                      value={editableTargetCompaniesText}
                      onChange={(event) => {
                        if (draftCalibrationProjectId !== selectedProject.id) {
                          setScorecardText(defaultScorecardText)
                        }
                        setDraftCalibrationProjectId(selectedProject.id)
                        setTargetCompaniesText(event.target.value)
                      }}
                    />
                  </label>
                  <label className="flex flex-col gap-2 text-sm">
                    <span className="font-medium text-primary-foreground">
                      Must-have scorecard
                    </span>
                    <Textarea
                      rows={10}
                      value={editableScorecardText}
                      onChange={(event) => {
                        if (draftCalibrationProjectId !== selectedProject.id) {
                          setTargetCompaniesText(defaultTargetCompaniesText)
                        }
                        setDraftCalibrationProjectId(selectedProject.id)
                        setScorecardText(event.target.value)
                      }}
                    />
                  </label>
                </div>
                <div className="mt-4 flex flex-wrap gap-2">
                  <Button
                    disabled={approvingProject}
                    onClick={() => void handleApprove()}
                    type="button"
                  >
                    {approvingProject ? 'Approving...' : 'Approve calibration'}
                  </Button>
                  <Button
                    disabled={
                      runningSearch || selectedProject.status === 'awaiting_calibration'
                    }
                    onClick={() => void handleRunSearch()}
                    type="button"
                    variant="secondary"
                  >
                    {runningSearch ? 'Searching...' : 'Run / refresh search'}
                  </Button>
                  <Button
                    disabled={selectedProject.projectCandidates.length === 0}
                    onClick={() => downloadCsv(selectedProject)}
                    type="button"
                    variant="outline"
                  >
                    Download CSV
                  </Button>
                </div>
                <div className="mt-4 text-xs text-secondary-foreground">
                  Keywords: {selectedProject.searchKeywords.join(', ')}
                </div>
              </SectionContainer>

              <SectionContainer title="Candidate map" titleClassName="text-base">
                <div className="mt-4 flex flex-col gap-3">
                  {selectedProject.projectCandidates.length === 0 ? (
                    <div className="text-sm text-secondary-foreground">
                      Approve calibration, then run search to generate candidates.
                    </div>
                  ) : null}
                  {selectedProject.projectCandidates.map((projectCandidate) => (
                    <CandidateCard
                      key={projectCandidate.id}
                      onFeedback={handleFeedback}
                      projectCandidate={projectCandidate}
                    />
                  ))}
                </div>
              </SectionContainer>
            </>
          ) : (
            <SectionContainer title="Create your first map" titleClassName="text-base">
              <div className="mt-4 text-sm text-secondary-foreground">
                Paste a JD and website to generate target companies and a scorecard.
              </div>
            </SectionContainer>
          )}
        </div>
      </div>

      {visibleErrorMessage ? (
        <div className="rounded-md border border-red-500 bg-red-700 p-3 text-sm text-red-200">
          {visibleErrorMessage}
        </div>
      ) : null}
    </div>
  )
}

const CandidateCard = ({
  projectCandidate,
  onFeedback,
}: {
  projectCandidate: ProjectCandidate
  onFeedback: (
    projectCandidate: ProjectCandidate,
    feedbackStatus: string
  ) => Promise<void>
}) => {
  const candidate = projectCandidate.candidate
  return (
    <div className="rounded-md border border-neutral-750 bg-neutral-850 p-4">
      <div className="flex flex-col gap-3 md:flex-row md:items-start md:justify-between">
        <div>
          <a
            className="font-medium text-blue-200 hover:text-blue-100"
            href={candidate.linkedinUrl}
            rel="noreferrer"
            target="_blank"
          >
            {candidate.fullName}
          </a>
          <div className="mt-1 text-sm text-secondary-foreground">
            {candidate.currentTitle} · {candidate.currentCompany}
          </div>
          <div className="mt-1 text-xs text-tertiary">
            {candidate.location} · {candidate.locationConfidence} NYC · seen in{' '}
            {candidate.associatedProjectCount} project
            {candidate.associatedProjectCount === 1 ? '' : 's'}
          </div>
        </div>
        <div className="grid grid-cols-3 gap-2 text-center text-xs">
          <ScorePill label="Fit" value={`${projectCandidate.fitScore}/100`} />
          <ScorePill label="Must-have" value={projectCandidate.mustHaveScore} />
          <ScorePill label="Sources" value={projectCandidate.sourceConfidence} />
        </div>
      </div>
      <p className="mt-3 text-sm text-secondary-foreground">
        {projectCandidate.rationale}
      </p>
      <div className="mt-3 flex flex-wrap gap-2 text-xs">
        <span className="rounded-full bg-neutral-750 px-2 py-1">
          Early-stage: {projectCandidate.earlyStageSignal}
        </span>
        <span className="rounded-full bg-neutral-750 px-2 py-1">
          Match: {projectCandidate.targetCompanyMatch}
        </span>
        {projectCandidate.domainTags.map((tag) => (
          <span className="rounded-full bg-blue-900 px-2 py-1" key={tag}>
            {tag}
          </span>
        ))}
        {candidate.githubUrl ? (
          <a
            className="rounded-full bg-neutral-750 px-2 py-1 text-blue-200"
            href={candidate.githubUrl}
            rel="noreferrer"
            target="_blank"
          >
            GitHub
          </a>
        ) : null}
      </div>
      <div className="mt-3 flex flex-wrap gap-2">
        {[
          ['good_fit', 'Good fit'],
          ['bad_fit', 'Bad fit'],
          ['not_relevant', 'Not relevant'],
        ].map(([value, label]) => (
          <Button
            key={value}
            onClick={() => void onFeedback(projectCandidate, value)}
            type="button"
            variant={projectCandidate.feedbackStatus === value ? 'default' : 'outline'}
          >
            {label}
          </Button>
        ))}
      </div>
    </div>
  )
}

const ScorePill = ({ label, value }: { label: string; value: string }) => (
  <div className="rounded-md border border-neutral-750 px-3 py-2">
    <div className="text-tertiary">{label}</div>
    <div className="mt-1 font-medium text-primary-foreground">{value}</div>
  </div>
)

export default SourcingDashboard
