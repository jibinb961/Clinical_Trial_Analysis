Studies
Returns data of studies matching query and filter parameters. The studies are returned page by page. If response contains nextPageToken, use its value in pageToken to get next page. The last page will not contain nextPageToken. A page may have empty studies array. Request for each subsequent page must have the same parameters as for the first page, except countTotal, pageSize, and pageToken parameters.

If neither queries nor filters are set, all studies will be returned. If any query parameter contains only NCT IDs (comma- and/or space-separated), filters are ignored.

query.* parameters are in Essie expression syntax. Those parameters affect ranking of studies, if sorted by relevance. See sort parameter for details.

filter.* and postFilter.* parameters have same effect as there is no aggregation calculation. Both are available just to simplify applying parameters from search request. Both do not affect ranking of studies.

Note: When trying JSON format in your browser, do not set too large pageSize parameter, if fields is unlimited. That may return too much data for the browser to parse and render.

REQUEST
QUERY-STRING PARAMETERS
format
enum
	
Default: json
Allowed: csv ┃ json
Must be one of the following:

csv- return CSV table with one page of study data; first page will contain header with column names; available fields are listed on CSV Download page
json- return JSON with one page of study data; every study object is placed in a separate line; markup type fields format depends on markupFormat parameter
markupFormat
enum
	
Default: markdown
Allowed: markdown ┃ legacy
Format of markup type fields:

markdown- markdown format
legacy- compatible with classic PRS
Applicable only to json format.

query.cond
string
	
"Conditions or disease" query in Essie expression syntax. See "ConditionSearch Area" on Search Areas for more details.

Examples: lung cancer  ┃ (head OR neck) AND pain
query.term
string
	
"Other terms" query in Essie expression syntax. See "BasicSearch Area" on Search Areas for more details.

Examples: AREA[LastUpdatePostDate]RANGE[2023-01-15,MAX]
query.locn
string
	
"Location terms" query in Essie expression syntax. See "LocationSearch Area" on Search Areas for more details.

query.titles
string
	
"Title / acronym" query in Essie expression syntax. See "TitleSearch Area" on Search Areas for more details.

query.intr
string
	
"Intervention / treatment" query in Essie expression syntax. See "InterventionSearch Area" on Search Areas for more details.

query.outc
string
	
"Outcome measure" query in Essie expression syntax. See "OutcomeSearch Area" on Search Areas for more details.

query.spons
string
	
"Sponsor / collaborator" query in Essie expression syntax. See "SponsorSearch Area" on Search Areas for more details.

query.lead
string
	
Searches in "LeadSponsorName" field. See Study Data Structure for more details. The query is in Essie expression syntax.

query.id
string
	
"Study IDs" query in Essie expression syntax. See "IdSearch Area" on Search Areas for more details.

query.patient
string
	
See "PatientSearch Area" on Search Areas for more details.

filter.overallStatus
array of string
 	
Allowed: ACTIVE_NOT_RECRUITING ┃ COMPLETED ┃ ENROLLING_BY_INVITATION ┃ NOT_YET_RECRUITING ┃ RECRUITING ┃ SUSPENDED ┃ TERMINATED ┃ WITHDRAWN ┃ AVAILABLE ┃ NO_LONGER_AVAILABLE ┃ TEMPORARILY_NOT_AVAILABLE ┃ APPROVED_FOR_MARKETING ┃ WITHHELD ┃ UNKNOWN
Filter by comma- or pipe-separated list of statuses

Examples: [ NOT_YET_RECRUITING, RECRUITING  ] ┃ [ COMPLETED  ]
filter.geo
string
	
Pattern: ^distance\(-?\d+(\.\d+)?,-?\d+(\.\d+)?,\d+(\.\d+)?(km|mi)?\)$
Filter by geo-function. Currently only distance function is supported. Format: distance(latitude,longitude,distance)

Examples: distance(39.0035707,-77.1013313,50mi)
filter.ids
array of string
 	
Filter by comma- or pipe-separated list of NCT IDs (a.k.a. ClinicalTrials.gov identifiers). The provided IDs will be searched in NCTId and NCTIdAlias fields.

Examples: [ NCT04852770, NCT01728545, NCT02109302  ]
filter.advanced
string
	
Filter by query in Essie expression syntax

Examples: AREA[StartDate]2022  ┃ AREA[MinimumAge]RANGE[MIN, 16 years] AND AREA[MaximumAge]RANGE[16 years, MAX]
filter.synonyms
array of string
 	
Filter by comma- or pipe-separated list of area:synonym_id pairs

Examples: [ ConditionSearch:1651367, BasicSearch:2013558  ]
postFilter.overallStatus
array of string
 	
Allowed: ACTIVE_NOT_RECRUITING ┃ COMPLETED ┃ ENROLLING_BY_INVITATION ┃ NOT_YET_RECRUITING ┃ RECRUITING ┃ SUSPENDED ┃ TERMINATED ┃ WITHDRAWN ┃ AVAILABLE ┃ NO_LONGER_AVAILABLE ┃ TEMPORARILY_NOT_AVAILABLE ┃ APPROVED_FOR_MARKETING ┃ WITHHELD ┃ UNKNOWN
Filter by comma- or pipe-separated list of statuses

Examples: [ NOT_YET_RECRUITING, RECRUITING  ] ┃ [ COMPLETED  ]
postFilter.geo
string
	
Pattern: ^distance\(-?\d+(\.\d+)?,-?\d+(\.\d+)?,\d+(\.\d+)?(km|mi)?\)$
Filter by geo-function. Currently only distance function is supported. Format: distance(latitude,longitude,distance)

Examples: distance(39.0035707,-77.1013313,50mi)
postFilter.ids
array of string
 	
Filter by comma- or pipe-separated list of NCT IDs (a.k.a. ClinicalTrials.gov identifiers). The provided IDs will be searched in NCTId and NCTIdAlias fields.

Examples: [ NCT04852770, NCT01728545, NCT02109302  ]
postFilter.advanced
string
	
Filter by query in Essie expression syntax

Examples: AREA[StartDate]2022  ┃ AREA[MinimumAge]RANGE[MIN, 16 years] AND AREA[MaximumAge]RANGE[16 years, MAX]
postFilter.synonyms
array of string
 	
Filter by comma- or pipe-separated list of area:synonym_id pairs

Examples: [ ConditionSearch:1651367, BasicSearch:2013558  ]
aggFilters
string
	
Apply aggregation filters, aggregation counts will not be provided. The value is comma- or pipe-separated list of pairs filter_id:space-separated list of option keys for the checked options.

Examples: results:with,status:com  ┃ status:not rec,sex:f,healthy:y
geoDecay
string
	
Default: func:exp,scale:300mi,offset:0mi,decay:0.5
Pattern: ^func:(gauss|exp|linear),scale:(\d+(\.\d+)?(km|mi)),offset:(\d+(\.\d+)?(km|mi)),decay:(\d+(\.\d+)?)$
Set proximity factor by distance from filter.geo location to the closest LocationGeoPoint of a study. Ignored, if filter.geo parameter is not set or response contains more than 10,000 studies.

Examples: func:linear,scale:100km,offset:10km,decay:0.1  ┃ func:gauss,scale:500mi,offset:0mi,decay:0.3
fields
array of string
 	
Min 1 item
If specified, must be non-empty comma- or pipe-separated list of fields to return. If unspecified, all fields will be returned. Order of the fields does not matter.

For csv format, specify list of columns. The column names are available on CSV Download.

For json format, every list item is either area name, piece name, field name, or special name. If a piece or a field is a branch node, all descendant fields will be included. All area names are available on Search Areas, the piece and field names — on Data Structure and also can be retrieved at /studies/metadata endpoint. There is a special name, @query, which expands to all fields queried by search.

Examples: [ NCTId, BriefTitle, OverallStatus, HasResults  ] ┃ [ ProtocolSection  ]
sort
array of string
 	
Max 2 items
Comma- or pipe-separated list of sorting options of the studies. The returning studies are not sorted by default for a performance reason. Every list item contains a field/piece name and an optional sort direction (asc for ascending or desc for descending) after colon character.

All piece and field names can be found on Data Structure and also can be retrieved at /studies/metadata endpoint. Currently, only date and numeric fields are allowed for sorting. There is a special "field" @relevance to sort by relevance to a search query.

Studies missing sort field are always last. Default sort direction:

Date field - desc
Numeric field - asc
@relevance - desc
Examples: [ @relevance  ] ┃ [ LastUpdatePostDate  ] ┃ [ EnrollmentCount:desc, NumArmGroups  ]
countTotal
boolean
	
Default: false
Count total number of studies in all pages and return totalCount field with first page, if true. For CSV, the result can be found in x-total-count response header. The parameter is ignored for the subsequent pages.

pageSize
int32
	
Default: 10
Min 0
Page size is maximum number of studies to return in response. It does not have to be the same for every page. If not specified or set to 0, the default value will be used. It will be coerced down to 1,000, if greater than that.

Examples: 2  ┃ 100
pageToken
string
	
Token to get next page. Set it to a nextPageToken value returned with the previous page in JSON format. For CSV, it can be found in x-next-page-token response header. Do not specify it for first page.

API Server
https://clinicaltrials.gov/api/v2
Authentication
Not Required