API Migration Guide
On this page
Introduction
Info API endpoints
Query API endpoints
Other endpoints
Study data model
Introduction
Endpoints, request parameters, and response schemas have changed significantly between the new API and classic. Study data are available for retrieval mainly in the JSON format; XML is supported only in the legacy endpoints. If you're using legacy JSON, you have to migrate to the new JSON API, using the migration guide.

"Legacy endpoints" in our new system are designed to replicate the behavior of classic system endpoints as closely as possible. This approach aims to ensure a smooth migration for existing clients of the classic site's API, allowing them to transition at their own pace without immediately adopting the full suite of new JSON API v2 features.

The path for the Classic API endpoints starts with /api/info/ or /api/query/. The path for the new API endpoints starts with /api/v2/. The path for the legacy API support endpoints starts with /api/legacy/.

Download content for all study records
To download a zip file containing the content for all study records available on ClinicalTrials.gov, refer to the following endpoints and documentation:

All Public XMLs
All API XMLs
Each zip file contains multiple directories that subdivide the large number of files into more manageable quantities. A top level "Contents.txt" file contains information about the number of study records and the date the studies were published.

Note: These zip files are very large and will likely take several minutes to download. Additionally, many receiving systems may subject the file to automatic security/virus scanning. This scanning may take several additional minutes to complete before the .Zip file is ready for use.
Info API endpoints
Access information about the version and structure of the ClinicalTrials.gov study records. The path for these endpoints starts with /api/info/.
GET /api/info/data_vrs — Data version
Returns the date when the ClinicalTrials.gov dataset was posted.

New endpoint: /api/v2/version (interactive documentation)

Check dataTimestamp field in the returned JSON.

Legacy endpoint support: /api/legacy/full-studies and /api/legacy/study-fields

Response from the classic endpoints contains DataVrs tag. To get an XML for empty results, parameter expr can be set to NOT ALL.
GET /api/info/api_vrs — API version
Returns the current version number of the ClinicalTrials.gov API. The API version number changes when the study structure changes (e.g., fields added) or when the API features change.

Legacy endpoint support: /api/legacy/full-studies and /api/legacy/study-fields

Legacy API support has its own version separate from the modern /api/v2/version endpoint. It is available in response from the classic endpoints in ApiVrs tag. To get an XML for empty results, parameter expr can be set to NOT ALL.
GET /api/info/api_defs — API definitions
Returns detailed definitions, like data elements for a single study record, search areas, and some statistics.

New endpoints: /api/v2/studies/metadata (interactive documentation), /api/v2/studies/search-areas (interactive documentation), /api/v2/stats/field/values (interactive documentation), /api/v2/stats/field/sizes (interactive documentation)

Different types of information provided by the classic endpoint can be retrieved using the new endpoints listed above.
GET /api/info/study_structure — Study structure
Returns all available data elements for a single study record.

New endpoint: /api/v2/studies/metadata (interactive documentation)

Provides the study data model for modern API. Please check the Study Data Model section below for the list of changes.
GET /api/info/study_fields_list — Study fields list
Returns all data elements that can be used in fields parameter of /api/query/study_fields endpoint.

Legacy endpoint support: /api/legacy/study-fields-list

Returns all fields that can be used in fields parameter of /api/legacy/study-fields endpoint. Only XML format is supported.
GET /api/info/study_statistics — Study statistics
Returns an annotated version of the Study Structure info endpoint.

New endpoints: /api/v2/studies/metadata (interactive documentation), /api/v2/stats/field/values (interactive documentation), /api/v2/stats/field/sizes (interactive documentation)

Different types of information provided by the classic endpoint can be retrieved using the new endpoints listed above.
GET /api/info/search_areas — Search areas
Returns an annotated version of the Study Structure info URL.

New endpoint: /api/v2/studies/search-areas (interactive documentation)

Search areas are provided only for Study document.
Query API endpoints
Performs a search, ranks the retrieved study records, and returns derived information about them. The path for these endpoints starts with /api/query/.
GET /api/query/full_studies — Full studies
This endpoint returns all content for a set of study records.

New endpoint: /api/v2/studies (interactive documentation)

The Search expression, classic expr parameter, can be set in the query.term parameter. Note: The default search areas for the classic and new API full studies endpoints are different, however, most can be tested using the search user interface.

The file format for response results may be either CSV or JSON. Responses are paginated with a default of 10 studies per response and a maximum of 1000.

Legacy endpoint support: /api/legacy/full-studies

Parameters are the same as for the classic endpoint. XML schema is FullStudiesResponse.xsd. Limitations are as follows:

Only XML format is supported
If the parameter expr is set, only the first 10,000 studies can be retrieved
GET /api/query/study_fields — Study fields
This endpoint returns values from selected API fields for a large set of study records.

New endpoint: /api/v2/studies (interactive documentation)

In fields parameter, you can set the fields you want to return values for. The returned data will have the structure of a full study but will only contain the specified fields.

The file format for response results may be either CSV or JSON. Responses are paginated with a default of 10 studies per response and a maximum of 1000.

Legacy endpoint support: /api/legacy/study-fields

Parameters are the same as for the classic endpoint. XML schema is StudyFieldsResponse.xsd. Limitations are as follows:

Only XML format is supported
Fields FlowReasonNumUnits and OrgStudyIdDomain are not available, but these fields contain no data in any study.
If the parameter expr is set, only the first 10,000 studies can be retrieved
GET /api/query/field_values — Field values
This endpoint returns all values found in a single API field for all study records.

New endpoints: /api/v2/stats/field/values (interactive documentation) and /api/v2/studies (interactive documentation)

These are not a complete replacement for the Classic endpoint. The first one, /api/v2/stats/field/values, does not accept a search expression and always returns the values for all studies, plus the number of returning values is limited to 250.

The second endpoint, /api/v2/studies, can be used instead of using the classic endpoint to get the NCTId field. The legacy expr parameter can be set in query.term parameter. Set the fields parameter to NCTId and get the results in JSON or CSV format.
Other endpoints
Other endpoints to access study data.
GET /ct2/show/{nctId}?displayxml=true — Single study data excluding results
This endpoint returns single study record data without results.

New endpoint: /api/v2/studies/{nctId} (interactive documentation)

Replace the path parameter {nctId} with an NCT number to get study data in modern JSON format. Use the fields parameter to select the data elements you want. Use the markupFormat parameter, if you want to change the format of markup fields.

Legacy endpoint support: /api/legacy/public-xml/{nctId}

XML schema is public.xsd.
GET /ct2/show/{nctId}?resultsxml=true — Single study data including results
This endpoint returns data for a single study records including results.

New endpoint: /api/v2/studies/{nctId} (interactive documentation)

Replace the path parameter {nctId} with an NCT number to get study data in modern JSON format. Use the fields parameter to select the data elements you want. Use the markupFormat parameter, if you want to change the format of markup fields.

Legacy endpoint support: /api/legacy/public-xml/{nctId}?full=true

XML schema is public.xsd.
GET /AllPublicXML.zip — All Public XMLs
This is a Zip archive containing all public data in XML format.

New endpoint: /api/v2/studies/download?format=json.zip

This Zip archive contains all the data in the new JSON format. The JSON schema of each file is the same as the response of /api/v2/studies/{nctId} endpoint (interactive documentation).

Legacy endpoint support: /api/legacy/public-xml?format=zip

XML schema is public.xsd.
GET /AllAPIXML.zip — All API XMLs
This is a Zip archive containing all Full Studies data in XML format.

New endpoint: /api/v2/studies/download?format=json.zip

This Zip archive contains all the data in the new JSON format. The JSON schema of each file is the same as the response of /api/v2/studies/{nctId} endpoint (interactive documentation).

Legacy endpoint support: /api/legacy/api-xml?format=zip

XML schema is FullStudiesResponse.xsd.
GET /ct2/download_studies — Download studies
This endpoint returns Zip archive containing matching studies in XML format. The search options are set in cond, term, lead, id, and other request parameters.

New endpoint: /api/v2/studies (interactive documentation)

Legacy endpoint support: /api/legacy/public-xml?format=zip&term=…

All search options must be converted into one search expression and put into the term parameter. If you only used the term parameter in the classic endpoint, copy the parameter value into the legacy term parameter. In other cases, enclose every parameter value into the AREA operator with the appropriate search area and combine them using the AND Boolean operator. For example, cond=cancer&term=treatment should be converted to query AREA[ConditionSearch]​cancer AND AREA[BasicSearch]​treatment and used as /api/legacy/public-xml?format=zip&term=AREA%5BConditionSearch%5Dcancer%20AND%20AREA%5BBasicSearch%5Dtreatment

XML schema is public.xsd.
Study data model
Study data were normalized. Field names are shorter and reused in the same structures. For example, PrimaryOutcome, SecondaryOutcome, and OtherOutcome contain the same three subfields: measure, description, and timeFrame. This allows them to be processed in the same manner.

Refer to the Study Data Structure page to compare how legacy field names are mapped to new field names. In Full or Table view modes, legacy field paths are listed as Classic XPath, New field paths are listed as Index Field.

Lists are declared as arrays. There are no wrappers for lists anymore. The JSON name of such fields takes the plural form (e.g. conditions).

Some fields have been converted and several have been added. Please see the changes below.
Date fields
All date field values are in ISO 8601 format now. Possible formats are:

yyyy
yyyy-MM
yyyy-MM-dd
yyyy-MM-dd'T'HH:mm
You can check formats and other stats of date fields on /stats/field-values?types=DATE or in Stats / Field Values (choose "DATE" type and click "Try").

Previously there were instances of Unknown string in SubmissionUnreleaseDate and UnpostedEventDate fields. Now date-type fields may contain only dates. Two new boolean fields added for such "Unknown" values - SubmissionUnreleaseDateUnknown and UnpostedEventDateUnknown - they are true in these cases.
Markup fields
Markup field values are in markdown format now. If you need them in legacy format, the /api/v2/studies and /api/v2/studies/{nctId} endpoints use the markupFormat parameter, which can be set to legacy.
Markup to text conversion
The following fields were converted from markup to text because there is no markup in the existing data and the Protocol and Registration Results System (PRS) does not allow entry of formatted text in them:

BriefTitle
OfficialTitle
Text to boolean conversion
The following fields were converted from text to boolean type:

AgreementPISponsorEmployee
BaselineMeasureCalculatePct
OutcomeMeasureCalculatePct
DelayedPosting
ExpAccTypeIndividual
ExpAccTypeIntermediate
ExpAccTypeTreatment
FDAAA801Violation
GenderBased
IsPPSD
IsUnapprovedDevice
IsUSExport
LargeDocNoSAP
AgreementRestrictiveAgreement
OversightHasDMC
OutcomeAnalysisTestedNonInferiority
PatientRegistry
HealthyVolunteers
Text to enum conversion
The following fields were converted from text to enumeration:

AgreementRestrictionType: enum AgreementRestrictionType
LTE60 → LTE60
GT60 → GT60
OTHER → OTHER
ArmGroupType: enum ArmGroupType
Experimental → EXPERIMENTAL
Active Comparator → ACTIVE_COMPARATOR
Placebo Comparator → PLACEBO_COMPARATOR
Sham Comparator → SHAM_COMPARATOR
No Intervention → NO_INTERVENTION
Other → OTHER
BaselineMeasureDispersionType: enum MeasureDispersionType
Not Applicable → NA
Standard Deviation → STANDARD_DEVIATION
Standard Error → STANDARD_ERROR
Inter-Quartile Range → INTER_QUARTILE_RANGE
Full Range → FULL_RANGE
80% Confidence Interval → CONFIDENCE_80
90% Confidence Interval → CONFIDENCE_90
95% Confidence Interval → CONFIDENCE_95
97.5% Confidence Interval → CONFIDENCE_975
99% Confidence Interval → CONFIDENCE_99
Other Confidence Interval Level → CONFIDENCE_OTHER
Geometric Coefficient of Variation → GEOMETRIC_COEFFICIENT
BaselineMeasureParamType: enum MeasureParam
Geometric Mean → GEOMETRIC_MEAN
Geometric Least Squares Mean → GEOMETRIC_LEAST_SQUARES_MEAN
Least Squares Mean → LEAST_SQUARES_MEAN
Log Mean → LOG_MEAN
Mean → MEAN
Median → MEDIAN
Number → NUMBER
Count of Participants → COUNT_OF_PARTICIPANTS
Count of Units → COUNT_OF_UNITS
BioSpecRetention: enum BioSpecRetention
None Retained → NONE_RETAINED
Samples With DNA → SAMPLES_WITH_DNA
Samples Without DNA → SAMPLES_WITHOUT_DNA
CentralContactRole: enum ContactRole
Study Chair → STUDY_CHAIR
Study Director → STUDY_DIRECTOR
Principal Investigator → PRINCIPAL_INVESTIGATOR
Sub-Investigator → SUB_INVESTIGATOR
Contact → CONTACT
CollaboratorClass: enum AgencyClass
NIH → NIH
FED → FED
OTHER_GOV → OTHER_GOV
INDIV → INDIV
INDUSTRY → INDUSTRY
NETWORK → NETWORK
AMBIG → AMBIG
OTHER → OTHER
UNKNOWN → UNKNOWN
CompletionDateType: enum DateType
Actual → ACTUAL
Estimate → ESTIMATED
ConditionBrowseLeafRelevance: enum BrowseLeafRelevance
low → LOW
high → HIGH
DesignAllocation: enum DesignAllocation
Randomized → RANDOMIZED
Non-Randomized → NON_RANDOMIZED
N/A → NA
DesignInterventionModel: enum InterventionalAssignment
Single Group Assignment → SINGLE_GROUP
Parallel Assignment → PARALLEL
Crossover Assignment → CROSSOVER
Factorial Assignment → FACTORIAL
Sequential Assignment → SEQUENTIAL
DesignMasking: enum DesignMasking
None (Open Label) → NONE
Single → SINGLE
Double → DOUBLE
Triple → TRIPLE
Quadruple → QUADRUPLE
DesignObservationalModel: enum ObservationalModel
Cohort → COHORT
Case-Control → CASE_CONTROL
Case-Only → CASE_ONLY
Case-Crossover → CASE_CROSSOVER
Ecologic or Community → ECOLOGIC_OR_COMMUNITY
Family-Based → FAMILY_BASED
Defined Population → DEFINED_POPULATION
Natural History → NATURAL_HISTORY
Other → OTHER
DesignPrimaryPurpose: enum PrimaryPurpose
Treatment → TREATMENT
Prevention → PREVENTION
Diagnostic → DIAGNOSTIC
Educational/Counseling/Training → ECT
Supportive Care → SUPPORTIVE_CARE
Screening → SCREENING
Health Services Research → HEALTH_SERVICES_RESEARCH
Basic Science → BASIC_SCIENCE
Device Feasibility → DEVICE_FEASIBILITY
Other → OTHER
DesignTimePerspective: enum DesignTimePerspective
Retrospective → RETROSPECTIVE
Prospective → PROSPECTIVE
Cross-Sectional → CROSS_SECTIONAL
Other → OTHER
DesignWhoMasked: enum WhoMasked
Participant → PARTICIPANT
Care Provider → CARE_PROVIDER
Investigator → INVESTIGATOR
Outcomes Assessor → OUTCOMES_ASSESSOR
DispFirstPostDateType: enum DateType
Actual → ACTUAL
Anticipated → ESTIMATED
EnrollmentType: enum EnrollmentType
Actual → ACTUAL
Anticipated → ESTIMATED
ExpandedAccessStatusForNCTId: enum ExpandedAccessStatus
Available → AVAILABLE
No longer available → NO_LONGER_AVAILABLE
Temporarily not available → TEMPORARILY_NOT_AVAILABLE
Approved for marketing → APPROVED_FOR_MARKETING
FirstMCPPostDateType: enum DateType
Actual → ACTUAL
Estimate → ESTIMATED
IPDSharing: enum IpdSharing
Yes → YES
No → NO
Undecided → UNDECIDED
IPDSharingInfoType: enum IpdSharingInfoType
Study Protocol → STUDY_PROTOCOL
Statistical Analysis Plan (SAP) → SAP
Informed Consent Form (ICF) → ICF
Clinical Study Report (CSR) → CSR
Analytic Code → ANALYTIC_CODE
InterventionBrowseLeafRelevance: enum BrowseLeafRelevance
low → LOW
high → HIGH
InterventionType: enum InterventionType
Behavioral → BEHAVIORAL
Biological → BIOLOGICAL
Combination Product → COMBINATION_PRODUCT
Device → DEVICE
Diagnostic Test → DIAGNOSTIC_TEST
Dietary Supplement → DIETARY_SUPPLEMENT
Drug → DRUG
Genetic → GENETIC
Procedure → PROCEDURE
Radiation → RADIATION
Other → OTHER
LastKnownStatus: enum Status
Active, not recruiting → ACTIVE_NOT_RECRUITING
Completed → COMPLETED
Enrolling by invitation → ENROLLING_BY_INVITATION
Not yet recruiting → NOT_YET_RECRUITING
Recruiting → RECRUITING
Suspended → SUSPENDED
Terminated → TERMINATED
Withdrawn → WITHDRAWN
Available → AVAILABLE
No longer available → NO_LONGER_AVAILABLE
Temporarily not available → TEMPORARILY_NOT_AVAILABLE
Approved for marketing → APPROVED_FOR_MARKETING
Withheld → WITHHELD
Unknown status → UNKNOWN
LastUpdatePostDateType: enum DateType
Actual → ACTUAL
Anticipated → ESTIMATED
LeadSponsorClass: enum AgencyClass
NIH → NIH
FED → FED
OTHER_GOV → OTHER_GOV
INDIV → INDIV
INDUSTRY → INDUSTRY
NETWORK → NETWORK
AMBIG → AMBIG
OTHER → OTHER
UNKNOWN → UNKNOWN
LocationContactRole: enum ContactRole
Study Chair → STUDY_CHAIR
Study Director → STUDY_DIRECTOR
Principal Investigator → PRINCIPAL_INVESTIGATOR
Sub-Investigator → SUB_INVESTIGATOR
Contact → CONTACT
LocationStatus: enum RecruitmentStatus
Active, not recruiting → ACTIVE_NOT_RECRUITING
Completed → COMPLETED
Enrolling by invitation → ENROLLING_BY_INVITATION
Not yet recruiting → NOT_YET_RECRUITING
Recruiting → RECRUITING
Suspended → SUSPENDED
Terminated → TERMINATED
Withdrawn → WITHDRAWN
Available → AVAILABLE
OrgClass: enum AgencyClass
NIH → NIH
FED → FED
OTHER_GOV → OTHER_GOV
INDIV → INDIV
INDUSTRY → INDUSTRY
NETWORK → NETWORK
AMBIG → AMBIG
OTHER → OTHER
UNKNOWN → UNKNOWN
OrgStudyIdType: enum OrgStudyIdType
U.S. NIH Grant/Contract → NIH
U.S. FDA Grant/Contract → FDA
U.S. VA Grant/Contract → VA
U.S. CDC Grant/Contract → CDC
U.S. AHRQ Grant/Contract → AHRQ
U.S. SAMHSA Grant/Contract → SAMHSA
OtherEventAssessmentType: enum EventAssessment
Non-systematic Assessment → NON_SYSTEMATIC_ASSESSMENT
Systematic Assessment → SYSTEMATIC_ASSESSMENT
OutcomeAnalysisCINumSides: enum ConfidenceIntervalNumSides
1-Sided → ONE_SIDED
2-Sided → TWO_SIDED
OutcomeAnalysisDispersionType: enum AnalysisDispersionType
Standard Deviation → STANDARD_DEVIATION
Standard Error of the Mean → STANDARD_ERROR_OF_MEAN
OutcomeAnalysisNonInferiorityType: enum NonInferiorityType
Superiority → SUPERIORITY
Non-Inferiority → NON_INFERIORITY
Equivalence → EQUIVALENCE
Other → OTHER
Non-Inferiority or Equivalence → NON_INFERIORITY_OR_EQUIVALENCE
Superiority or Other → SUPERIORITY_OR_OTHER
Non-Inferiority or Equivalence (legacy) → NON_INFERIORITY_OR_EQUIVALENCE_LEGACY
Superiority or Other (legacy) → SUPERIORITY_OR_OTHER_LEGACY
OutcomeMeasureParamType: enum MeasureParam
Geometric Mean → GEOMETRIC_MEAN
Geometric Least Squares Mean → GEOMETRIC_LEAST_SQUARES_MEAN
Least Squares Mean → LEAST_SQUARES_MEAN
Log Mean → LOG_MEAN
Mean → MEAN
Median → MEDIAN
Number → NUMBER
Count of Participants → COUNT_OF_PARTICIPANTS
Count of Units → COUNT_OF_UNITS
OutcomeMeasureReportingStatus: enum ReportingStatus
Not Posted → NOT_POSTED
Posted → POSTED
OutcomeMeasureType: enum OutcomeMeasureType
Primary → PRIMARY
Secondary → SECONDARY
Other Pre-specified → OTHER_PRE_SPECIFIED
Post-Hoc → POST_HOC
OverallOfficialRole: enum OfficialRole
Study Chair → STUDY_CHAIR
Study Director → STUDY_DIRECTOR
Principal Investigator → PRINCIPAL_INVESTIGATOR
Sub-Investigator → SUB_INVESTIGATOR
OverallStatus: enum Status
Active, not recruiting → ACTIVE_NOT_RECRUITING
Completed → COMPLETED
Enrolling by invitation → ENROLLING_BY_INVITATION
Not yet recruiting → NOT_YET_RECRUITING
Recruiting → RECRUITING
Suspended → SUSPENDED
Terminated → TERMINATED
Withdrawn → WITHDRAWN
Available → AVAILABLE
No longer available → NO_LONGER_AVAILABLE
Temporarily not available → TEMPORARILY_NOT_AVAILABLE
Approved for marketing → APPROVED_FOR_MARKETING
Withheld → WITHHELD
Unknown status → UNKNOWN
Phase: enum Phase
Not Applicable → NA
Early Phase 1 → EARLY_PHASE1
Phase 1 → PHASE1
Phase 2 → PHASE2
Phase 3 → PHASE3
Phase 4 → PHASE4
PrimaryCompletionDateType: enum DateType
Actual → ACTUAL
Estimate → ESTIMATED
ReferenceType: enum ReferenceType
background → BACKGROUND
result → RESULT
derived → DERIVED
ResponsiblePartyType: enum ResponsiblePartyType
Sponsor → SPONSOR
Principal Investigator → PRINCIPAL_INVESTIGATOR
Sponsor-Investigator → SPONSOR_INVESTIGATOR
ResultsFirstPostDateType: enum DateType
Actual → ACTUAL
Anticipated → ESTIMATED
SamplingMethod: enum SamplingMethod
Probability Sample → PROBABILITY_SAMPLE
Non-Probability Sample → NON_PROBABILITY_SAMPLE
SecondaryIdType: enum SecondaryIdType
U.S. NIH Grant/Contract → NIH
U.S. FDA Grant/Contract → FDA
U.S. VA Grant/Contract → VA
U.S. CDC Grant/Contract → CDC
U.S. AHRQ Grant/Contract → AHRQ
U.S. SAMHSA Grant/Contract → SAMHSA
Other Grant/Funding Number → OTHER_GRANT
EudraCT Number → EUDRACT_NUMBER
EU Trial (CTIS) Number → CTIS
Registry Identifier → REGISTRY
Other Identifier → OTHER
SeriousEventAssessmentType: enum EventAssessment
Non-systematic Assessment → NON_SYSTEMATIC_ASSESSMENT
Systematic Assessment → SYSTEMATIC_ASSESSMENT
Sex: enum Sex
Female → FEMALE
Male → MALE
All → ALL
StartDateType: enum DateType
Actual → ACTUAL
Estimate → ESTIMATED
StdAge: enum StandardAge
Child → CHILD
Adult → ADULT
Older Adult → OLDER_ADULT
StudyFirstPostDateType: enum DateType
Actual → ACTUAL
Anticipated → ESTIMATED
StudyType: enum StudyType
Expanded Access → EXPANDED_ACCESS
Interventional → INTERVENTIONAL
Observational → OBSERVATIONAL
UnpostedEventType: enum UnpostedEventType
Reset → RESET
Release → RELEASE
Unrelease → UNRELEASE
ViolationEventType: enum ViolationEventType
Violation Identified by FDA → VIOLATION_IDENTIFIED
Correction Confirmed by FDA → CORRECTION_CONFIRMED
Penalty Imposed by FDA → PENALTY_IMPOSED
Issues in letter addressed; confirmed by FDA. → ISSUES_IN_LETTER_ADDRESSED_CONFIRMED
List to single value conversion
The following fields were converted from list to a single value type:

DesignObservationalModel
DesignTimePerspective
Added fields
The following fields were added to the returning data:

HasResults
LocationGeoPoint
UnpostedEventDateUnknown
SubmissionUnreleaseDateUnknown
Last updated on August 27, 2024