# Global News Intelligence Platform — Comprehensive Source Discovery

**Research / inventory date:** 2026-07-19  
**Master source universe:** 384 sources  
**Phase 1:** 190 sources  
**Phase 2:** 194 sources  

## Scope and architecture alignment

This source-discovery inventory was built for the Global News Intelligence Platform v0.1 architecture. The acquisition policy is operationally tiered: reliable native RSS/Atom first; RSSHub or RSS-Bridge/custom bridges where a generated discovery feed is practical; ordinary HTTP scraping before browser automation; Playwright only for JavaScript/WAF/anti-bot cases; changedetection.io for low-volume government and institutional pages; and YouTube channel discovery plus yt-dlp/transcript processing for video sources.

Editorial-orientation labels are approximate monitoring metadata, not reliability scores. They are included only where a broad orientation is reasonably established or useful for viewpoint balancing.

**Verification caveat:** core current sources, representative native-RSS pages, and key government pages were web-verified during the July 2026 research pass. The rest are established monitoring sources but must still pass an automated production endpoint health check before activation. RSS availability and source activity are tracked separately because a live publisher can have a stale historical feed.

## Master inventory counts

| Country / region | Sources | Phase 1 | Phase 2 |
|---|---:|---:|---:|
| United States | 77 | 35 | 42 |
| South Korea | 61 | 30 | 31 |
| Japan | 53 | 25 | 28 |
| Taiwan | 42 | 22 | 20 |
| China | 48 | 25 | 23 |
| North Korea / DPRK Monitoring | 22 | 15 | 7 |
| Philippines | 41 | 20 | 21 |
| Indo-Pacific / Regional | 40 | 18 | 22 |

### Ingestion counts

- Native RSS as primary method: **97**
- RSSHub / RSS-Bridge candidates: **105**
- Direct scraping or Playwright: **140**
- Government/institutional changedetection.io targets: **97**
- YouTube / yt-dlp candidates: **72**
- Technically difficult/problematic sources flagged: **75**

## Country and regional source sections

# United States

## Major National / Political News

| Source | Organization type | Orientation | Language / English | Official status | Ingestion | RSS / feed page | YouTube | Priority / Phase | Topics | Value / access notes |
|---|---|---|---|---|---|---|---|---|---|---|
| [Politico](https://www.politico.com/) | Political news organization | Mainstream / politics-specialist | English / EN: Yes | No | Native RSS | https://www.politico.com/rss/politicopicks.xml | https://www.youtube.com/@POLITICO | Critical / Phase 1 | Congress; White House; elections; policy; EU | High-value national, political, legal, investigative, or agenda-setting U.S. source. Premium products paywalled. |
| [ABC News](https://abcnews.go.com/) | Broadcast/digital news | Mainstream | English / EN: Yes | No | Native RSS | https://abcnews.go.com/abcnews/topstories | https://www.youtube.com/@ABCNews | High / Phase 1 | National; politics; world; investigations | High-value national, political, legal, investigative, or agenda-setting U.S. source. Legacy-style feed endpoints; parser health-check. |
| [CBS News](https://www.cbsnews.com/) | Broadcast/digital news | Mainstream | English / EN: Yes | No | Native RSS | https://www.cbsnews.com/latest/rss/main | https://www.youtube.com/@CBSNews | High / Phase 1 | National; politics; investigations; world | High-value national, political, legal, investigative, or agenda-setting U.S. source. Verify category feeds. |
| [CNN](https://www.cnn.com/) | Cable news / digital publisher | Mainstream / center-left perceived | English / EN: Yes | No | Native RSS | http://rss.cnn.com/rss/edition.rss | https://www.youtube.com/@CNN | High / Phase 1 | Breaking news; politics; world; business | High-value national, political, legal, investigative, or agenda-setting U.S. source. Legacy RSS endpoints can be inconsistent; health-check. |
| [NBC News](https://www.nbcnews.com/) | Broadcast/digital news | Mainstream | English / EN: Yes | No | Native RSS | https://feeds.nbcnews.com/nbcnews/public/news | https://www.youtube.com/@NBCNews | High / Phase 1 | National; politics; investigations; world | High-value national, political, legal, investigative, or agenda-setting U.S. source. Full-text article scraping may still be needed. |
| [PBS NewsHour](https://www.pbs.org/newshour/) | Public television news | Public media / mainstream | English / EN: Yes | No | Native RSS | https://www.pbs.org/newshour/feeds/rss/headlines | https://www.youtube.com/@PBSNewsHour | High / Phase 2 | Politics; policy; foreign affairs; interviews | High-value national, political, legal, investigative, or agenda-setting U.S. source. Video adds primary-source value. |
| [RealClearPolitics](https://www.realclearpolitics.com/) | Aggregator / political analysis | Center / aggregation across viewpoints | English / EN: Yes | No | Direct scraping | — | — | High / Phase 2 | Politics; government; policy; media narratives | High-value monitoring source for the platform. |
| [The Hill](https://thehill.com/) | Political newspaper/digital outlet | Mainstream / politics-specialist | English / EN: Yes | No | Native RSS | https://thehill.com/news/feed/ | https://www.youtube.com/@thehill | High / Phase 2 | Congress; White House; elections; media | High-value national, political, legal, investigative, or agenda-setting U.S. source. Full-text scraping needed beyond feed. |

## Regional & Local News

| Source | Organization type | Orientation | Language / English | Official status | Ingestion | RSS / feed page | YouTube | Priority / Phase | Topics | Value / access notes |
|---|---|---|---|---|---|---|---|---|---|---|
| [Associated Press (AP)](https://apnews.com/) | News cooperative / wire service | Mainstream / wire service | English / EN: Yes | No | Direct scraping | — | — | Critical / Phase 1 | Breaking news; elections; courts; states; federal government | High-value national, political, legal, investigative, or agenda-setting U.S. source. Public feeds limited; licensing terms matter for full-text reuse. |
| [NPR](https://www.npr.org/) | Public radio / digital news | Public media / mainstream | English / EN: Yes | No | Native RSS | https://feeds.npr.org/1001/rss.xml | https://www.youtube.com/@NPR | High / Phase 2 | National; politics; culture; world; public policy | High-value national, political, legal, investigative, or agenda-setting U.S. source. Review feed/reuse terms. |
| [USA Today](https://www.usatoday.com/) | National newspaper | Mainstream | English / EN: Yes | No | Direct scraping | — | — | High / Phase 2 | Politics; government; policy; media narratives | High-value monitoring source for the platform. |

## Independent & Investigative Media

| Source | Organization type | Orientation | Language / English | Official status | Ingestion | RSS / feed page | YouTube | Priority / Phase | Topics | Value / access notes |
|---|---|---|---|---|---|---|---|---|---|---|
| [The New York Times](https://www.nytimes.com/) | Newspaper | Mainstream / center-left leaning editorial page | English / EN: Yes | No | Native RSS | https://rss.nytimes.com/services/xml/rss/nyt/HomePage.xml | — | Critical / Phase 1 | Politics; investigations; courts; world; business | High-value national, political, legal, investigative, or agenda-setting U.S. source. Metered/paywalled; feed usually discovery/summary. |
| [The Washington Post](https://www.washingtonpost.com/) | Newspaper | Mainstream / center-left leaning editorial page | English / EN: Yes | No | Native RSS | https://www.washingtonpost.com/rss/ | — | Critical / Phase 1 | Politics; federal government; national security; local DC | High-value national, political, legal, investigative, or agenda-setting U.S. source. Paywall; category RSS available; full text may require subscription session. |
| [ProPublica](https://www.propublica.org/) | Nonprofit investigative newsroom | Independent / nonprofit | English / EN: Yes | No | Native RSS | https://feeds.propublica.org/propublica/main | https://www.youtube.com/@propublica | High / Phase 2 | Government accountability; justice; data investigations | High-value national, political, legal, investigative, or agenda-setting U.S. source. Generally accessible; respect reuse terms. |
| [The Intercept](https://theintercept.com/) | Investigative digital outlet | Progressive / left-leaning | English / EN: Yes | No | Native RSS | https://theintercept.com/feed/?rss | — | High / Phase 2 | Politics; government; policy; media narratives | High-value monitoring source for the platform. |
| [Mother Jones](https://www.motherjones.com/) | Magazine | Progressive / left-leaning | English / EN: Yes | No | Native RSS | https://www.motherjones.com/feed/ | — | Medium / Phase 2 | Politics; government; policy; media narratives | High-value monitoring source for the platform. |

## Political / Ideological & YouTube Media

| Source | Organization type | Orientation | Language / English | Official status | Ingestion | RSS / feed page | YouTube | Priority / Phase | Topics | Value / access notes |
|---|---|---|---|---|---|---|---|---|---|---|
| [Breitbart News](https://www.breitbart.com/) | Digital media | Right-leaning / populist conservative | English / EN: Yes | No | Native RSS | https://www.breitbart.com/feed/ | https://www.youtube.com/@BreitbartNews | High / Phase 2 | Politics; government; policy; media narratives | High-value monitoring source for the platform. |
| [Fox News](https://www.foxnews.com/) | Cable news / digital publisher | Conservative / right-leaning | English / EN: Yes | No | Native RSS | https://moxie.foxnews.com/google-publisher/latest.xml | https://www.youtube.com/@FoxNews | High / Phase 1 | Politics; elections; national news; opinion | High-value national, political, legal, investigative, or agenda-setting U.S. source. Separate news/opinion where possible. |
| [National Review](https://www.nationalreview.com/) | Magazine | Conservative / right-leaning | English / EN: Yes | No | Native RSS | https://www.nationalreview.com/feed/ | https://www.youtube.com/@nationalreview | High / Phase 2 | Politics; government; policy; media narratives | High-value monitoring source for the platform. |
| [Washington Examiner](https://www.washingtonexaminer.com/) | Newspaper/digital | Conservative / right-leaning | English / EN: Yes | No | Direct scraping | — | — | High / Phase 2 | Politics; government; policy; media narratives | High-value monitoring source for the platform. |
| [The Daily Wire](https://www.dailywire.com/) | Digital media | Conservative / right-leaning | English / EN: Yes | No | Direct scraping | — | — | Medium / Phase 2 | Politics; government; policy; media narratives | High-value monitoring source for the platform. Some subscription/paywall or membership content may apply. |
| [The Federalist](https://thefederalist.com/) | Digital magazine | Conservative / right-leaning | English / EN: Yes | No | Native RSS | https://thefederalist.com/feed/ | — | Medium / Phase 2 | Politics; government; policy; media narratives | High-value monitoring source for the platform. |

## Business & Financial News

| Source | Organization type | Orientation | Language / English | Official status | Ingestion | RSS / feed page | YouTube | Priority / Phase | Topics | Value / access notes |
|---|---|---|---|---|---|---|---|---|---|---|
| [Reuters U.S.](https://www.reuters.com/world/us/) | International news agency | Mainstream / wire service | English / EN: Yes | No | Direct scraping | — | — | Critical / Phase 1 | National politics; economy; courts; foreign affairs | High-value national, political, legal, investigative, or agenda-setting U.S. source. Public RSS limited; licensing/redistribution restrictions; licensed/API access preferable. |
| [The Wall Street Journal](https://www.wsj.com/) | Newspaper | Center-right editorial page; mainstream news desk | English / EN: Yes | No | Direct scraping | — | — | Critical / Phase 1 | Markets; business; politics; technology; China | High-value national, political, legal, investigative, or agenda-setting U.S. source. Hard paywall/anti-bot; licensed access preferable. |

## Defense, Military, Intelligence & Geopolitics

| Source | Organization type | Orientation | Language / English | Official status | Ingestion | RSS / feed page | YouTube | Priority / Phase | Topics | Value / access notes |
|---|---|---|---|---|---|---|---|---|---|---|
| [Breaking Defense](https://breakingdefense.com/) | Defense publication | Specialist / mainstream defense | English / EN: Yes | No | Native RSS | https://breakingdefense.com/feed/ | — | Critical / Phase 1 | Defense; foreign policy; China; Indo-Pacific; technology; national security | High-value monitoring source for the platform. |
| [Defense News](https://www.defensenews.com/) | Defense trade publication | Mainstream / defense trade | English / EN: Yes | No | Native RSS | https://www.defensenews.com/rss/ | — | Critical / Phase 1 | Defense; foreign policy; China; Indo-Pacific; technology; national security | High-value monitoring source for the platform. |
| [USNI News](https://news.usni.org/) | Naval publication | Specialist / naval | English / EN: Yes | No | Native RSS | https://news.usni.org/feed | — | Critical / Phase 1 | Defense; foreign policy; China; Indo-Pacific; technology; national security | High-value monitoring source for the platform. |
| [Defense One](https://www.defenseone.com/) | Defense/government publication | Mainstream / defense policy | English / EN: Yes | No | Direct scraping | — | — | High / Phase 2 | Defense; foreign policy; China; Indo-Pacific; technology; national security | High-value monitoring source for the platform. |
| [The War Zone](https://www.twz.com/) | Defense publication | Specialist | English / EN: Yes | No | Native RSS | https://www.twz.com/feed | — | High / Phase 2 | Defense; foreign policy; China; Indo-Pacific; technology; national security | High-value monitoring source for the platform. |
| [War on the Rocks](https://warontherocks.com/) | National-security publication | Specialist / realist-policy mix | English / EN: Yes | No | Native RSS | https://warontherocks.com/feed/ | — | High / Phase 2 | Defense; foreign policy; China; Indo-Pacific; technology; national security | High-value monitoring source for the platform. |

## Technology & Cybersecurity

| Source | Organization type | Orientation | Language / English | Official status | Ingestion | RSS / feed page | YouTube | Priority / Phase | Topics | Value / access notes |
|---|---|---|---|---|---|---|---|---|---|---|
| [Bloomberg](https://www.bloomberg.com/) | Financial news organization | Mainstream / business-focused | English / EN: Yes | No | Direct scraping | — | — | Critical / Phase 1 | Markets; companies; government; technology; geopolitics | High-value national, political, legal, investigative, or agenda-setting U.S. source. Strong paywall/anti-bot; licensed/API access preferable. |
| [CISA](https://www.cisa.gov/) | Federal agency | Official | English / EN: Yes | Yes - official U.S. government | Native RSS | https://www.cisa.gov/news.xml | https://www.youtube.com/@CISAgov | Critical / Phase 1 | Cyber alerts; vulnerabilities; infrastructure security | Primary-source U.S. government, legal, security, or military information. |
| [Axios](https://www.axios.com/) | Digital news outlet | Mainstream / centrist-style concise reporting | English / EN: Yes | No | Direct scraping | — | — | High / Phase 2 | Politics; business; tech; national security | High-value national, political, legal, investigative, or agenda-setting U.S. source. Newsletter-heavy; no broad RSS verified. |
| [Federal News Network](https://federalnewsnetwork.com/) | Trade/public-sector news | Nonpartisan / public-sector specialist | English / EN: Yes | No | Native RSS | https://federalnewsnetwork.com/feed/ | — | High / Phase 2 | Politics; government; policy; media narratives | High-value monitoring source for the platform. |
| [Semafor](https://www.semafor.com/) | Digital news outlet | Mainstream / global | English / EN: Yes | No | Direct scraping | — | — | Medium / Phase 2 | Politics; government; policy; media narratives | High-value monitoring source for the platform. |

## Legislatures, Courts & Election Authorities

| Source | Organization type | Orientation | Language / English | Official status | Ingestion | RSS / feed page | YouTube | Priority / Phase | Topics | Value / access notes |
|---|---|---|---|---|---|---|---|---|---|---|
| [Congress.gov](https://www.congress.gov/) | Legislative information system | Official | English / EN: Yes | Yes - official U.S. institution | Native RSS | https://www.congress.gov/rss | — | Critical / Phase 1 | Bills; resolutions; floor schedules; nominations | Primary-source U.S. government, legal, security, or military information. |
| [Department of Justice](https://www.justice.gov/) | Federal department | Official | English / EN: Yes | Yes - official U.S. government | Native RSS | https://www.justice.gov/feeds/press_releases.xml | https://www.youtube.com/@TheJusticeDepartment | Critical / Phase 1 | Prosecutions; antitrust; national security; civil rights | Primary-source U.S. government, legal, security, or military information. |
| [Supreme Court of the United States](https://www.supremecourt.gov/) | Court | Official | English / EN: Yes | Yes - official U.S. institution | changedetection.io | — | — | Critical / Phase 1 | Opinions; orders; oral arguments; docket | Primary-source U.S. government, legal, security, or military information. PDF-heavy or decentralized sub-sites may require targeted monitors. |
| [U.S. Courts](https://www.uscourts.gov/) | Judiciary system | Official | English / EN: Yes | Yes - official U.S. institution | changedetection.io | — | — | High / Phase 2 | Court administration; rules; federal court news | Primary-source U.S. government, legal, security, or military information. PDF-heavy or decentralized sub-sites may require targeted monitors. |
| [U.S. House of Representatives](https://www.house.gov/) | Legislature | Official | English / EN: Yes | Yes - official U.S. institution | changedetection.io | — | — | High / Phase 2 | House floor; committees; leadership | Primary-source U.S. government, legal, security, or military information. PDF-heavy or decentralized sub-sites may require targeted monitors. |
| [U.S. Senate](https://www.senate.gov/) | Legislature | Official | English / EN: Yes | Yes - official U.S. institution | changedetection.io | — | — | High / Phase 2 | Senate floor; committees; nominations | Primary-source U.S. government, legal, security, or military information. PDF-heavy or decentralized sub-sites may require targeted monitors. |

## Government, Executive, Defense, Security & Law Enforcement

| Source | Organization type | Orientation | Language / English | Official status | Ingestion | RSS / feed page | YouTube | Priority / Phase | Topics | Value / access notes |
|---|---|---|---|---|---|---|---|---|---|---|
| [Federal Register](https://www.federalregister.gov/) | Official government publication | Official | English / EN: Yes | Yes - official U.S. government | Native RSS | https://www.federalregister.gov/documents/search.rss | — | Critical / Phase 1 | Rules; notices; executive orders; proposed regulations | Primary-source U.S. government, legal, security, or military information. |
| [U.S. Department of Defense](https://www.defense.gov/) | Defense ministry | Official | English / EN: Yes | Yes - official U.S. government | Native RSS | https://www.defense.gov/DesktopModules/ArticleCS/RSS.ashx?ContentType=400&Site=945&Category=Press%20Releases | https://www.youtube.com/@DeptofDefense | Critical / Phase 1 | Defense policy; operations; contracts; leadership | Primary-source U.S. government, legal, security, or military information. |
| [U.S. Department of State](https://www.state.gov/) | Foreign ministry | Official | English / EN: Yes | Yes - official U.S. government | changedetection.io | — | https://www.youtube.com/@StateDept | Critical / Phase 1 | Diplomacy; sanctions; treaties; press briefings | Primary-source U.S. government, legal, security, or military information. PDF-heavy or decentralized sub-sites may require targeted monitors. |
| [U.S. Indo-Pacific Command](https://www.pacom.mil/) | Military combatant command | Official | English / EN: Yes | Yes - official U.S. government | changedetection.io | — | — | Critical / Phase 1 | Indo-Pacific operations; exercises; posture | Primary-source U.S. government, legal, security, or military information. PDF-heavy or decentralized sub-sites may require targeted monitors. |
| [U.S. Navy](https://www.navy.mil/) | Military branch | Official | English / EN: Yes | Yes - official U.S. government | YouTube/yt-dlp | — | https://www.youtube.com/@USNavy | Critical / Phase 1 | Naval operations; Indo-Pacific; exercises | Primary-source U.S. government, legal, security, or military information. |
| [White House](https://www.whitehouse.gov/) | Executive office | Official | English / EN: Yes | Yes - official U.S. government | changedetection.io | — | https://www.youtube.com/@WhiteHouse | Critical / Phase 1 | Presidential actions; speeches; fact sheets; briefings | Primary-source U.S. government, legal, security, or military information. PDF-heavy or decentralized sub-sites may require targeted monitors. |
| [Central Intelligence Agency](https://www.cia.gov/) | Intelligence agency | Official | English / EN: Yes | Yes - official U.S. government | changedetection.io | — | — | High / Phase 2 | Intelligence; statements; declassified material | Primary-source U.S. government, legal, security, or military information. PDF-heavy or decentralized sub-sites may require targeted monitors. |
| [Department of Homeland Security](https://www.dhs.gov/) | Federal department | Official | English / EN: Yes | Yes - official U.S. government | Native RSS | https://www.dhs.gov/news/rss | — | High / Phase 1 | Border; immigration; cyber; security | Primary-source U.S. government, legal, security, or military information. |
| [Federal Bureau of Investigation](https://www.fbi.gov/) | Federal law enforcement | Official | English / EN: Yes | Yes - official U.S. government | Native RSS | https://www.fbi.gov/feeds/fbi-in-the-news/rss.xml | https://www.youtube.com/@FBI | High / Phase 1 | Investigations; counterintelligence; cyber; crime | Primary-source U.S. government, legal, security, or military information. |
| [National Security Agency](https://www.nsa.gov/) | Intelligence agency | Official | English / EN: Yes | Yes - official U.S. government | changedetection.io | — | — | High / Phase 2 | Cybersecurity; cryptography; intelligence; advisories | Primary-source U.S. government, legal, security, or military information. PDF-heavy or decentralized sub-sites may require targeted monitors. |
| [Office of the Director of National Intelligence](https://www.dni.gov/) | Intelligence coordinating office | Official | English / EN: Yes | Yes - official U.S. government | changedetection.io | — | — | High / Phase 2 | Threat assessments; intelligence community statements | Primary-source U.S. government, legal, security, or military information. PDF-heavy or decentralized sub-sites may require targeted monitors. |
| [U.S. Air Force](https://www.af.mil/) | Military branch | Official | English / EN: Yes | Yes - official U.S. government | YouTube/yt-dlp | — | https://www.youtube.com/@usairforce | High / Phase 1 | Air operations; bases; modernization | Primary-source U.S. government, legal, security, or military information. |
| [U.S. Army](https://www.army.mil/) | Military branch | Official | English / EN: Yes | Yes - official U.S. government | YouTube/yt-dlp | — | https://www.youtube.com/@USArmy | High / Phase 1 | Army operations; modernization; exercises | Primary-source U.S. government, legal, security, or military information. |
| [U.S. Coast Guard](https://www.uscg.mil/) | Military / law enforcement | Official | English / EN: Yes | Yes - official U.S. government | YouTube/yt-dlp | — | https://www.youtube.com/@USCG | High / Phase 1 | Maritime security; interdiction; Pacific | Primary-source U.S. government, legal, security, or military information. |
| [U.S. Marine Corps](https://www.marines.mil/) | Military branch | Official | English / EN: Yes | Yes - official U.S. government | YouTube/yt-dlp | — | https://www.youtube.com/@marines | High / Phase 1 | Marine operations; amphibious forces; exercises | Primary-source U.S. government, legal, security, or military information. |
| [U.S. Space Force](https://www.spaceforce.mil/) | Military branch | Official | English / EN: Yes | Yes - official U.S. government | Direct scraping | — | — | High / Phase 2 | Space security; satellites; force structure | Primary-source U.S. government, legal, security, or military information. |

## Think Tanks, Research Institutes & Universities

| Source | Organization type | Orientation | Language / English | Official status | Ingestion | RSS / feed page | YouTube | Priority / Phase | Topics | Value / access notes |
|---|---|---|---|---|---|---|---|---|---|---|
| [Asia Maritime Transparency Initiative (CSIS)](https://amti.csis.org/) | Think tank project | Bipartisan / specialist | English / EN: Yes | No | Direct scraping | — | — | Critical / Phase 1 | Defense; foreign policy; China; Indo-Pacific; technology; national security | High-value monitoring source for the platform. |
| [Beyond Parallel (CSIS)](https://beyondparallel.csis.org/) | Think tank project | Bipartisan / specialist | English / EN: Yes | No | Direct scraping | — | — | Critical / Phase 1 | Defense; foreign policy; China; Indo-Pacific; technology; national security | High-value monitoring source for the platform. |
| [CSIS](https://www.csis.org/) | Think tank | Bipartisan / policy establishment | English / EN: Yes | No | Native RSS | https://www.csis.org/rss.xml | https://www.youtube.com/@csis | Critical / Phase 1 | Defense; foreign policy; China; Indo-Pacific; technology; national security | High-value monitoring source for the platform. |
| [Carnegie Endowment](https://carnegieendowment.org/) | Think tank | Center / international affairs | English / EN: Yes | No | Direct scraping | — | — | High / Phase 2 | Defense; foreign policy; China; Indo-Pacific; technology; national security | High-value monitoring source for the platform. |
| [Center for a New American Security](https://www.cnas.org/) | Think tank | Centrist / national-security | English / EN: Yes | No | Direct scraping | — | — | High / Phase 2 | Defense; foreign policy; China; Indo-Pacific; technology; national security | High-value monitoring source for the platform. |
| [ChinaPower Project (CSIS)](https://chinapower.csis.org/) | Think tank project | Bipartisan / specialist | English / EN: Yes | No | Direct scraping | — | — | High / Phase 2 | Defense; foreign policy; China; Indo-Pacific; technology; national security | High-value monitoring source for the platform. |
| [Council on Foreign Relations](https://www.cfr.org/) | Think tank | Nonpartisan / establishment | English / EN: Yes | No | Native RSS | https://www.cfr.org/rss.xml | https://www.youtube.com/@cfr | High / Phase 2 | Defense; foreign policy; China; Indo-Pacific; technology; national security | High-value monitoring source for the platform. |
| [Hudson Institute](https://www.hudson.org/) | Think tank | Conservative-leaning policy institute | English / EN: Yes | No | Native RSS | https://www.hudson.org/rss.xml | — | High / Phase 2 | Defense; foreign policy; China; Indo-Pacific; technology; national security | High-value monitoring source for the platform. |
| [RAND Corporation](https://www.rand.org/) | Research institute | Nonpartisan / policy research | English / EN: Yes | No | Native RSS | https://www.rand.org/pubs.rss | https://www.youtube.com/@RANDCorporation | High / Phase 2 | Defense; foreign policy; China; Indo-Pacific; technology; national security | High-value monitoring source for the platform. |
| [Atlantic Council](https://www.atlanticcouncil.org/) | Think tank | Center / Atlanticist | English / EN: Yes | No | Native RSS | https://www.atlanticcouncil.org/feed/ | https://www.youtube.com/@AtlanticCouncilUS | Medium / Phase 2 | Defense; foreign policy; China; Indo-Pacific; technology; national security | High-value monitoring source for the platform. |
| [Brookings Institution](https://www.brookings.edu/) | Think tank | Center / policy establishment | English / EN: Yes | No | Native RSS | https://www.brookings.edu/feed/ | — | Medium / Phase 2 | Defense; foreign policy; China; Indo-Pacific; technology; national security | High-value monitoring source for the platform. |
| [Heritage Foundation](https://www.heritage.org/) | Think tank | Conservative | English / EN: Yes | No | Native RSS | https://www.heritage.org/rss | — | Medium / Phase 2 | Defense; foreign policy; China; Indo-Pacific; technology; national security | High-value monitoring source for the platform. |
| [Stanford APARC](https://aparc.fsi.stanford.edu/) | University/policy center | Academic | English / EN: Yes | No | Direct scraping | — | — | Medium / Phase 2 | Defense; foreign policy; China; Indo-Pacific; technology; national security | High-value monitoring source for the platform. |
| [MIT Security Studies Program](https://ssp.mit.edu/) | University/policy center | Academic | English / EN: Yes | No | changedetection.io | — | — | Low / Phase 2 | Defense; foreign policy; China; Indo-Pacific; technology; national security | High-value monitoring source for the platform. |

## Other High-Value Sources

| Source | Organization type | Orientation | Language / English | Official status | Ingestion | RSS / feed page | YouTube | Priority / Phase | Topics | Value / access notes |
|---|---|---|---|---|---|---|---|---|---|---|
| [SCOTUSblog](https://www.scotusblog.com/) | Specialist legal publication | Independent / specialist | English / EN: Yes | No | Native RSS | https://www.scotusblog.com/feed/ | — | Critical / Phase 1 | Supreme Court; cases; orders; analysis | High-value national, political, legal, investigative, or agenda-setting U.S. source. Pair with Supreme Court primary source. |
| [Foreign Affairs](https://www.foreignaffairs.com/) | Magazine / think tank publication | Establishment / policy journal | English / EN: Yes | No | Direct scraping | — | — | High / Phase 2 | Defense; foreign policy; China; Indo-Pacific; technology; national security | High-value monitoring source for the platform. Paywall/subscription may apply. |
| [Foreign Policy](https://foreignpolicy.com/) | Magazine | Mainstream / internationalist | English / EN: Yes | No | Direct scraping | — | — | High / Phase 2 | Defense; foreign policy; China; Indo-Pacific; technology; national security | High-value monitoring source for the platform. Paywall/subscription may apply. |
| [Just Security](https://www.justsecurity.org/) | Academic/legal policy publication | Center-left / specialist | English / EN: Yes | No | Native RSS | https://www.justsecurity.org/feed/ | — | High / Phase 2 | National security law; human rights; war powers | High-value national, political, legal, investigative, or agenda-setting U.S. source. Analysis-focused. |
| [Lawfare](https://www.lawfaremedia.org/) | Nonprofit legal/national-security publication | Centrist / specialist | English / EN: Yes | No | Native RSS | https://www.lawfaremedia.org/rss.xml | — | High / Phase 2 | National security law; cyber; intelligence; courts | High-value national, political, legal, investigative, or agenda-setting U.S. source. Analysis and primary-document links. |
| [The Atlantic](https://www.theatlantic.com/) | Magazine | Center-left / liberal-leaning | English / EN: Yes | No | Direct scraping | — | — | Medium / Phase 2 | Politics; government; policy; media narratives | High-value monitoring source for the platform. Some subscription/paywall or membership content may apply. |

# South Korea

## Major National / Political News

| Source | Organization type | Orientation | Language / English | Official status | Ingestion | RSS / feed page | YouTube | Priority / Phase | Topics | Value / access notes |
|---|---|---|---|---|---|---|---|---|---|---|
| [KBS News](https://news.kbs.co.kr/) | Public broadcaster | Public broadcaster / mainstream | Korean / EN: Limited | No | YouTube/yt-dlp | — | https://www.youtube.com/@newskbs | Critical / Phase 1 | Politics; society; economy; world; North Korea | High-value Korean national, political, investigative, business, technology, or perspective source. Use KBS World RSS for English and YouTube/site for domestic Korean. |
| [KBS World Radio News](https://world.kbs.co.kr/) | Public international broadcaster | Public broadcaster / mainstream | English / EN: Yes | No | Native RSS | http://world.kbs.co.kr/rss/rss_news.htm?lang=e | — | Critical / Phase 1 | Korea politics; economy; diplomacy; North Korea | High-value Korean national, political, investigative, business, technology, or perspective source. Older HTTP feed endpoints; health-check. |
| [MBC News](https://news.mbc.co.kr/) | Public broadcaster | Public broadcaster / mainstream | Korean / EN: Limited | No | YouTube/yt-dlp | — | https://www.youtube.com/@MBCNEWS11 | Critical / Phase 1 | Politics; society; investigations; live news | High-value Korean national, political, investigative, business, technology, or perspective source. Website plus YouTube; no broad RSS verified. |
| [SBS News](https://news.sbs.co.kr/) | Commercial broadcaster | Mainstream | Korean / EN: Limited | No | Native RSS | https://news.sbs.co.kr/news/headlineRssFeed.do?plink=RSSREADER | https://www.youtube.com/@SBSnews8 | Critical / Phase 1 | Politics; society; economy; world; video | High-value Korean national, political, investigative, business, technology, or perspective source. Review RSS reuse terms. |
| [YTN](https://www.ytn.co.kr/) | 24-hour news network | Mainstream | Korean / EN: Limited | No | YouTube/yt-dlp | — | https://www.youtube.com/@YTN | Critical / Phase 1 | Breaking news; politics; weather; live events | High-value Korean national, political, investigative, business, technology, or perspective source. High-volume. |
| [JTBC News](https://news.jtbc.co.kr/) | Cable/broadcast news | Mainstream / center-left perceived | Korean / EN: Limited | No | YouTube/yt-dlp | — | https://www.youtube.com/@JTBC_news | High / Phase 2 | Politics; investigations; society; live coverage | High-value Korean national, political, investigative, business, technology, or perspective source. No native feed verified; video monitoring valuable. |
| [The Korea Herald](https://www.koreaherald.com/) | English-language newspaper | Mainstream | English / EN: Yes | No | Direct scraping | — | — | High / Phase 2 | Politics; diplomacy; business; culture | High-value Korean national, political, investigative, business, technology, or perspective source. |
| [The Korea Times](https://www.koreatimes.co.kr/) | English-language newspaper | Mainstream | English / EN: Yes | No | Direct scraping | — | — | High / Phase 2 | Politics; diplomacy; business; society | High-value Korean national, political, investigative, business, technology, or perspective source. |
| [Yonhap News TV (연합뉴스TV)](https://www.yonhapnewstv.co.kr/) | Cable news network | Mainstream | Korean / EN: Limited | No | YouTube/yt-dlp | — | https://www.youtube.com/@yonhapnewstv23 | High / Phase 2 | Breaking news; politics; live events | High-value Korean national, political, investigative, business, technology, or perspective source. Video-first; captions vary. |

## Regional & Local News

| Source | Organization type | Orientation | Language / English | Official status | Ingestion | RSS / feed page | YouTube | Priority / Phase | Topics | Value / access notes |
|---|---|---|---|---|---|---|---|---|---|---|
| [Newsis (뉴시스)](https://www.newsis.com/) | News agency | Mainstream / wire | Korean / EN: Limited | No | Native RSS | https://www.newsis.com/RSS/sokbo.xml | — | Critical / Phase 1 | Breaking; politics; international; economy; regional | High-value Korean national, political, investigative, business, technology, or perspective source. Feed is discovery layer; section feeds available. |
| [Yonhap News Agency (연합뉴스)](https://www.yna.co.kr/) | National news agency | Mainstream / national wire | Korean / EN: Yes | No | Direct scraping | — | — | Critical / Phase 1 | Politics; economy; diplomacy; North Korea; breaking news | High-value Korean national, political, investigative, business, technology, or perspective source. Robots/anti-bot restrictions; licensed/API access may be preferable. |
| [News1 Korea (뉴스1)](https://www.news1.kr/) | News agency | Mainstream / wire | Korean / EN: Limited | No | Direct scraping | — | — | High / Phase 2 | Politics; economy; society; regions; international | High-value Korean national, political, investigative, business, technology, or perspective source. Robots/access restrictions may require browser/licensed access. |

## Independent & Investigative Media

| Source | Organization type | Orientation | Language / English | Official status | Ingestion | RSS / feed page | YouTube | Priority / Phase | Topics | Value / access notes |
|---|---|---|---|---|---|---|---|---|---|---|
| [Newstapa (뉴스타파)](https://newstapa.org/) | Nonprofit investigative newsroom | Independent / investigative | Korean / EN: Limited | No | YouTube/yt-dlp | — | https://www.youtube.com/@newstapa | Critical / Phase 1 | Corruption; politics; investigations; data journalism | High-value Korean national, political, investigative, business, technology, or perspective source. Website scraping plus video/transcripts. |
| [OhmyNews (오마이뉴스)](https://www.ohmynews.com/) | Digital/citizen journalism outlet | Progressive / left-leaning | Korean / EN: Limited | No | Native RSS | https://rss.ohmynews.com/rss/ohmynews.xml | https://www.youtube.com/@OhmynewsTV | High / Phase 1 | Politics; society; citizen journalism; opinion | High-value Korean national, political, investigative, business, technology, or perspective source. Distinguish citizen contributions/opinion from staff reporting. |
| [Pressian (프레시안)](https://www.pressian.com/) | Digital newspaper | Progressive / left-leaning | Korean / EN: Limited | No | Direct scraping | — | — | Medium / Phase 2 | Politics; labor; society; opinion | High-value Korean national, political, investigative, business, technology, or perspective source. |

## Political / Ideological & YouTube Media

| Source | Organization type | Orientation | Language / English | Official status | Ingestion | RSS / feed page | YouTube | Priority / Phase | Topics | Value / access notes |
|---|---|---|---|---|---|---|---|---|---|---|
| [Chosun Ilbo (조선일보)](https://www.chosun.com/) | Newspaper | Conservative / right-leaning | Korean / EN: Yes | No | Direct scraping | — | — | Critical / Phase 1 | Politics; society; economy; world; opinion | High-value Korean national, political, investigative, business, technology, or perspective source. Some paywall/anti-bot; multilingual editions. |
| [Dong-A Ilbo (동아일보)](https://www.donga.com/) | Newspaper | Conservative / right-leaning | Korean / EN: Yes | No | Direct scraping | https://www.donga.com/news/RSS | — | Critical / Phase 1 | Politics; society; economy; world; opinion | High-value Korean national, political, investigative, business, technology, or perspective source. RSS link visible; exact endpoint discovery needed; reuse restrictions. |
| [Hankyoreh (한겨레)](https://www.hani.co.kr/) | Newspaper | Progressive / left-leaning | Korean / EN: Limited | No | Direct scraping | — | — | Critical / Phase 1 | Politics; labor; society; foreign affairs; opinion | High-value Korean national, political, investigative, business, technology, or perspective source. Robots/site access can complicate scraping. |
| [JoongAng Ilbo (중앙일보)](https://www.joongang.co.kr/) | Newspaper | Center-right / conservative | Korean / EN: Limited | No | Playwright | — | — | Critical / Phase 1 | Politics; society; business; opinion | High-value Korean national, political, investigative, business, technology, or perspective source. Robots/anti-bot restrictions observed. |
| [Kyunghyang Shinmun (경향신문)](https://www.khan.co.kr/) | Newspaper | Progressive / center-left | Korean / EN: Limited | No | Native RSS | https://www.khan.co.kr/rss/rssdata/total_news.xml | — | High / Phase 1 | Politics; society; economy; opinion | High-value Korean national, political, investigative, business, technology, or perspective source. |
| [Pennmike (펜앤드마이크)](https://www.pennmike.com/) | Digital media | Conservative / right-leaning | Korean / EN: Limited | No | YouTube/yt-dlp | — | https://www.youtube.com/@pennmike | High / Phase 2 | Politics; elections; commentary; security | High-value Korean national, political, investigative, business, technology, or perspective source. Video/opinion-heavy. |
| [김어준의 겸손은힘들다 뉴스공장](https://www.youtube.com/@gyeomsonisnothing) | Independent political YouTube | Progressive / left-leaning | Korean / EN: No | No | YouTube/yt-dlp | — | https://www.youtube.com/@gyeomsonisnothing | High / Phase 2 | Politics; elections; commentary; investigations | High-value Korean political/video monitoring source. Resolve and store immutable YouTube channel ID before production; handle may change. |
| [신의한수](https://www.youtube.com/@shinuihansu) | Independent political YouTube | Conservative / right-leaning | Korean / EN: No | No | YouTube/yt-dlp | — | https://www.youtube.com/@shinuihansu | High / Phase 2 | Politics; elections; commentary; investigations | High-value Korean political/video monitoring source. Resolve and store immutable YouTube channel ID before production; handle may change. |
| [펜앤드마이크TV](https://www.youtube.com/@pennmike) | Political/news YouTube | Conservative / right-leaning | Korean / EN: No | No | YouTube/yt-dlp | — | https://www.youtube.com/@pennmike | High / Phase 2 | Politics; elections; commentary; investigations | High-value Korean political/video monitoring source. Resolve and store immutable YouTube channel ID before production; handle may change. |
| [Dailyan (데일리안)](https://www.dailian.co.kr/) | Digital newspaper | Center-right / conservative | Korean / EN: Limited | No | Direct scraping | — | — | Medium / Phase 2 | Politics; economy; society | High-value Korean national, political, investigative, business, technology, or perspective source. |
| [New Daily (뉴데일리)](https://www.newdaily.co.kr/) | Digital newspaper | Conservative / right-leaning | Korean / EN: Limited | No | Direct scraping | — | — | Medium / Phase 2 | Politics; security; society; opinion | High-value Korean national, political, investigative, business, technology, or perspective source. Opinion-heavy. |
| [고성국TV](https://www.youtube.com/@kosungkuk) | Independent political YouTube | Conservative / right-leaning | Korean / EN: No | No | YouTube/yt-dlp | — | https://www.youtube.com/@kosungkuk | Medium / Phase 2 | Politics; elections; commentary; investigations | High-value Korean political/video monitoring source. Resolve and store immutable YouTube channel ID before production; handle may change. |
| [성창경TV](https://www.youtube.com/@sungchangkyung) | Independent political YouTube | Conservative / right-leaning | Korean / EN: No | No | YouTube/yt-dlp | — | https://www.youtube.com/@sungchangkyung | Medium / Phase 2 | Politics; elections; commentary; investigations | High-value Korean political/video monitoring source. Resolve and store immutable YouTube channel ID before production; handle may change. |

## Business & Financial News

| Source | Organization type | Orientation | Language / English | Official status | Ingestion | RSS / feed page | YouTube | Priority / Phase | Topics | Value / access notes |
|---|---|---|---|---|---|---|---|---|---|---|
| [Maeil Business Newspaper (매일경제)](https://www.mk.co.kr/) | Business newspaper | Business-focused / market-oriented | Korean / EN: Yes | No | Native RSS | https://www.mk.co.kr/rss/30000001/ | — | Critical / Phase 1 | Markets; companies; economy; politics | High-value Korean national, political, investigative, business, technology, or perspective source. Premium content may apply. |
| [Korea Economic Daily (한국경제)](https://www.hankyung.com/) | Business newspaper | Business-focused / market-oriented | Korean / EN: Limited | No | Direct scraping | — | — | High / Phase 2 | Economy; markets; companies; technology | High-value Korean national, political, investigative, business, technology, or perspective source. Some subscription products. |

## Technology & Cybersecurity

| Source | Organization type | Orientation | Language / English | Official status | Ingestion | RSS / feed page | YouTube | Priority / Phase | Topics | Value / access notes |
|---|---|---|---|---|---|---|---|---|---|---|
| [Boannews (보안뉴스)](https://www.boannews.com/) | Cybersecurity publication | Cybersecurity specialist | Korean / EN: Limited | No | Direct scraping | — | — | Critical / Phase 1 | Cyber incidents; vulnerabilities; policy; security industry | High-value Korean national, political, investigative, business, technology, or perspective source. |
| [Electronic Times (전자신문)](https://www.etnews.com/) | Technology newspaper | Technology/business specialist | Korean / EN: Limited | No | Native RSS | http://rss.etnews.com/Section901.xml | — | Critical / Phase 1 | Technology; semiconductors; telecom; cybersecurity | High-value Korean national, political, investigative, business, technology, or perspective source. Some HTTP feed endpoints. |
| [BusinessKorea](https://www.businesskorea.co.kr/) | Business English-language publication | Business-focused | English / EN: Yes | No | Native RSS | https://www.businesskorea.co.kr/rss/allArticle.xml | — | High / Phase 1 | Semiconductors; companies; industry; economy | High-value Korean national, political, investigative, business, technology, or perspective source. |
| [ZDNet Korea](https://zdnet.co.kr/) | Technology publication | Technology specialist | Korean / EN: Limited | No | Direct scraping | — | — | High / Phase 2 | Enterprise tech; AI; cybersecurity; semiconductors | High-value Korean national, political, investigative, business, technology, or perspective source. |
| [Korea Communications Commission](https://www.kcc.go.kr/) | Regulator | Official | Korean / EN: Limited | Yes - official South Korean government/institution | changedetection.io | — | — | Medium / Phase 2 | Media regulation; platforms; broadcasting | Primary-source South Korean government, legal, election, defense, or security information. Agency structure can change. |

## Legislatures, Courts & Election Authorities

| Source | Organization type | Orientation | Language / English | Official status | Ingestion | RSS / feed page | YouTube | Priority / Phase | Topics | Value / access notes |
|---|---|---|---|---|---|---|---|---|---|---|
| [Constitutional Court of Korea (헌법재판소)](https://www.ccourt.go.kr/) | Constitutional court | Official | Korean / EN: Yes | Yes - official South Korean government/institution | changedetection.io | — | — | Critical / Phase 1 | Constitutional decisions; hearings; press releases | Primary-source South Korean government, legal, election, defense, or security information. |
| [National Assembly (대한민국 국회)](https://www.assembly.go.kr/) | Legislature | Official | Korean / EN: Limited | Yes - official South Korean government/institution | changedetection.io | — | — | Critical / Phase 1 | Bills; committees; plenary sessions; press releases | Primary-source South Korean government, legal, election, defense, or security information. Multiple systems/subdomains. |
| [National Election Commission (중앙선거관리위원회)](https://www.nec.go.kr/) | Election commission | Official | Korean / EN: Limited | Yes - official South Korean government/institution | Native RSS | https://app.newsloth.com/nec-go-kr/WlpSWlc.rss | — | Critical / Phase 1 | Elections; rules; press releases; fact checks | Primary-source South Korean government, legal, election, defense, or security information. Feeds delivered through Newsloth; monitor dependency. |
| [Supreme Court of Korea (대한민국 법원)](https://www.scourt.go.kr/) | Court system | Official | Korean / EN: Limited | Yes - official South Korean government/institution | changedetection.io | — | — | Critical / Phase 1 | Judgments; court news; administration | Primary-source South Korean government, legal, election, defense, or security information. PDF/HWP attachments; dynamic pages. |

## Government, Executive, Defense, Security & Law Enforcement

| Source | Organization type | Orientation | Language / English | Official status | Ingestion | RSS / feed page | YouTube | Priority / Phase | Topics | Value / access notes |
|---|---|---|---|---|---|---|---|---|---|---|
| [Korea Policy Briefing (정책브리핑)](https://www.korea.kr/) | Government news portal | Official | Korean / EN: Limited | Yes - official South Korean government/institution | Direct scraping | — | — | Critical / Phase 1 | Cross-ministry policy; press releases; government news | Primary-source South Korean government, legal, election, defense, or security information. RSS service discontinued 2026-07-01; replace with scraping/change monitoring. |
| [Ministry of Foreign Affairs (외교부)](https://www.mofa.go.kr/) | Foreign ministry | Official | Korean / EN: Yes | Yes - official South Korean government/institution | changedetection.io | — | — | Critical / Phase 1 | Diplomacy; sanctions; treaties; briefings | Primary-source South Korean government, legal, election, defense, or security information. |
| [Ministry of National Defense (국방부)](https://www.mnd.go.kr/) | Defense ministry | Official | Korean / EN: Limited | Yes - official South Korean government/institution | changedetection.io | — | — | Critical / Phase 1 | Defense policy; military operations; exercises | Primary-source South Korean government, legal, election, defense, or security information. |
| [Ministry of Unification (통일부)](https://www.unikorea.go.kr/) | Government ministry | Official | Korean / EN: Yes | Yes - official South Korean government/institution | changedetection.io | — | — | Critical / Phase 1 | North Korea; inter-Korean relations; defectors | Primary-source South Korean government, legal, election, defense, or security information. |
| [Office of the President (대통령실)](https://www.president.go.kr/) | Executive office | Official | Korean / EN: Limited | Yes - official South Korean government/institution | changedetection.io | — | — | Critical / Phase 1 | Presidential speeches; briefings; appointments; policy | Primary-source South Korean government, legal, election, defense, or security information. |
| [ROK Joint Chiefs of Staff (합동참모본부)](https://www.jcs.mil.kr/) | Military command | Official | Korean / EN: Limited | Yes - official South Korean government/institution | changedetection.io | — | — | Critical / Phase 1 | North Korea activity; exercises; operational statements | Primary-source South Korean government, legal, election, defense, or security information. Low-volume high-value. |
| [Korean National Police Agency (경찰청)](https://www.police.go.kr/) | Police agency | Official | Korean / EN: Limited | Yes - official South Korean government/institution | changedetection.io | — | — | High / Phase 2 | Crime; investigations; public safety | Primary-source South Korean government, legal, election, defense, or security information. |
| [National Intelligence Service (국가정보원)](https://www.nis.go.kr/) | Intelligence agency | Official | Korean / EN: Limited | Yes - official South Korean government/institution | changedetection.io | — | — | High / Phase 2 | Counterintelligence; cyber; North Korea; public notices | Primary-source South Korean government, legal, election, defense, or security information. Sparse publishing. |
| [Republic of Korea Air Force](https://www.airforce.mil.kr/) | Military branch | Official | Korean / EN: Limited | Yes - official South Korean government/institution | changedetection.io | — | — | High / Phase 2 | Air operations; exercises; procurement | Primary-source South Korean government, legal, election, defense, or security information. |
| [Republic of Korea Army](https://www.army.mil.kr/) | Military branch | Official | Korean / EN: Limited | Yes - official South Korean government/institution | changedetection.io | — | — | High / Phase 2 | Army operations; exercises; personnel | Primary-source South Korean government, legal, election, defense, or security information. |
| [Republic of Korea Navy](https://www.navy.mil.kr/) | Military branch | Official | Korean / EN: Limited | Yes - official South Korean government/institution | changedetection.io | — | — | High / Phase 2 | Naval operations; exercises; ship activity | Primary-source South Korean government, legal, election, defense, or security information. |

## Think Tanks, Research Institutes & Universities

| Source | Organization type | Orientation | Language / English | Official status | Ingestion | RSS / feed page | YouTube | Priority / Phase | Topics | Value / access notes |
|---|---|---|---|---|---|---|---|---|---|---|
| [Asan Institute for Policy Studies](https://www.asaninst.org/) | Think tank | Center-right / policy institute | Korean / EN: Yes | No | Native RSS | https://www.asaninst.org/feed/ | — | High / Phase 1 | Foreign policy; alliances; China; North Korea | High-value monitoring source for the platform. |
| [Institute for National Security Strategy (INSS)](https://www.inss.re.kr/) | Research institute | Government-linked research | Korean / EN: Yes | No | Direct scraping | — | — | High / Phase 2 | National security; North Korea; intelligence | High-value monitoring source for the platform. PDF-heavy; extract publications and metadata. |
| [Korea Institute for Defense Analyses (KIDA)](https://www.kida.re.kr/) | Government-funded research institute | Government-funded research | Korean / EN: Yes | Government-funded research institute | Direct scraping | — | — | High / Phase 2 | Defense policy; military strategy; procurement | High-value monitoring source for the platform. PDF-heavy; extract publications and metadata. |
| [Korea Institute for International Economic Policy (KIEP)](https://www.kiep.go.kr/) | Government-funded research institute | Government-funded research | Korean / EN: Yes | Government-funded research institute | Direct scraping | — | — | High / Phase 2 | Trade; China; global economy; regional integration | High-value monitoring source for the platform. PDF-heavy; extract publications and metadata. |
| [Korea Institute for National Unification (KINU)](https://www.kinu.or.kr/) | Government-funded research institute | Government-funded research | Korean / EN: Yes | Government-funded research institute | Direct scraping | — | — | High / Phase 2 | North Korea; unification; human rights; policy | High-value monitoring source for the platform. PDF-heavy; extract publications and metadata. |
| [Sejong Institute](https://www.sejong.org/) | Think tank | Policy institute | Korean / EN: Yes | No | Direct scraping | — | — | High / Phase 2 | North Korea; diplomacy; security | High-value monitoring source for the platform. |
| [East Asia Institute (EAI)](https://www.eai.or.kr/) | Think tank | Independent / policy research | Korean / EN: Yes | No | Direct scraping | — | — | Medium / Phase 2 | Democracy; foreign policy; East Asia | High-value monitoring source for the platform. |
| [Seoul National University Institute for Peace and Unification Studies](https://ipus.snu.ac.kr/) | University/policy center | Academic | Korean / EN: Yes | No | Direct scraping | — | — | Medium / Phase 2 | North Korea; peace; unification; surveys | High-value monitoring source for the platform. |

## YouTube & Video Sources

| Source | Organization type | Orientation | Language / English | Official status | Ingestion | RSS / feed page | YouTube | Priority / Phase | Topics | Value / access notes |
|---|---|---|---|---|---|---|---|---|---|---|
| [뉴스타파](https://www.youtube.com/@newstapa) | Investigative YouTube | Independent / investigative | Korean / EN: No | No | YouTube/yt-dlp | — | https://www.youtube.com/@newstapa | Critical / Phase 1 | Politics; elections; commentary; investigations | High-value Korean political/video monitoring source. Resolve and store immutable YouTube channel ID before production; handle may change. |
| [오마이TV](https://www.youtube.com/@OhmynewsTV) | News/political YouTube | Progressive / left-leaning | Korean / EN: No | No | YouTube/yt-dlp | — | https://www.youtube.com/@OhmynewsTV | High / Phase 2 | Politics; elections; commentary; investigations | High-value Korean political/video monitoring source. Resolve and store immutable YouTube channel ID before production; handle may change. |

## Other High-Value Sources

| Source | Organization type | Orientation | Language / English | Official status | Ingestion | RSS / feed page | YouTube | Priority / Phase | Topics | Value / access notes |
|---|---|---|---|---|---|---|---|---|---|---|
| [SisaIN (시사IN)](https://www.sisain.co.kr/) | News magazine | Center-left / progressive-leaning | Korean / EN: Limited | No | Direct scraping | — | — | High / Phase 2 | Politics; society; investigations; analysis | High-value Korean national, political, investigative, business, technology, or perspective source. Some subscriber content. |

# Japan

## Major National / Political News

| Source | Organization type | Orientation | Language / English | Official status | Ingestion | RSS / feed page | YouTube | Priority / Phase | Topics | Value / access notes |
|---|---|---|---|---|---|---|---|---|---|---|
| [Jiji Press (時事通信)](https://www.jiji.com/) | News agency | Mainstream / wire | Japanese / EN: No | No | Direct scraping | — | — | Critical / Phase 1 | Politics; economy; bureaucracy; world | High-value Japanese national, regional, business, technology, investigative, or perspective source. |
| [NHK News Web](https://www3.nhk.or.jp/news/) | Public broadcaster | Public broadcaster / mainstream | Japanese / EN: Yes | No | Direct scraping | — | — | Critical / Phase 1 | Politics; disasters; economy; world; local | High-value Japanese national, regional, business, technology, investigative, or perspective source. Dynamic pages; no broad RSS verified; respect terms. |
| [Nippon.com](https://www.nippon.com/) | Multilingual nonprofit media | Mainstream / public-interest | Japanese / EN: Yes | No | Native RSS | https://www.nippon.com/en/feed/ | — | High / Phase 2 | Japan policy; society; economy; culture | High-value Japanese national, regional, business, technology, investigative, or perspective source. Health-check by language. |
| [The Japan Times](https://www.japantimes.co.jp/) | English-language newspaper | Mainstream | English / EN: Yes | No | Native RSS | https://www.japantimes.co.jp/feed/ | — | High / Phase 2 | Japan politics; society; business; foreign affairs | High-value Japanese national, regional, business, technology, investigative, or perspective source. Subscription/paywall on some content. |

## Regional & Local News

| Source | Organization type | Orientation | Language / English | Official status | Ingestion | RSS / feed page | YouTube | Priority / Phase | Topics | Value / access notes |
|---|---|---|---|---|---|---|---|---|---|---|
| [Kyodo News (共同通信)](https://www.kyodo.co.jp/) | News cooperative / wire service | Mainstream / wire | Japanese / EN: Yes | No | Direct scraping | — | — | Critical / Phase 1 | Politics; regions; foreign affairs; breaking news | High-value Japanese national, regional, business, technology, investigative, or perspective source. Public full-text limited; licensing may be preferable. |
| [Hokkaido Shimbun (北海道新聞)](https://www.hokkaido-np.co.jp/) | Regional newspaper | Regional mainstream | Japanese / EN: No | No | Direct scraping | — | — | High / Phase 2 | Hokkaido; Russia; defense; local politics | High-value Japanese national, regional, business, technology, investigative, or perspective source. Paywall possible. |
| [Nishinippon Shimbun (西日本新聞)](https://www.nishinippon.co.jp/) | Regional newspaper | Regional mainstream | Japanese / EN: No | No | Direct scraping | — | — | High / Phase 2 | Kyushu; Fukuoka; Korea/China proximity; local politics | High-value Japanese national, regional, business, technology, investigative, or perspective source. Paywall on some content. |
| [Chunichi Shimbun (中日新聞)](https://www.chunichi.co.jp/) | Regional newspaper | Regional mainstream | Japanese / EN: No | No | Direct scraping | — | — | Medium / Phase 2 | Chubu; industry; local politics | High-value Japanese national, regional, business, technology, investigative, or perspective source. |
| [Kahoku Shimpo (河北新報)](https://kahoku.news/) | Regional newspaper | Regional mainstream | Japanese / EN: No | No | Direct scraping | — | — | Medium / Phase 2 | Tohoku; disasters; local politics | High-value Japanese national, regional, business, technology, investigative, or perspective source. |
| [Kobe Shimbun (神戸新聞)](https://www.kobe-np.co.jp/) | Regional newspaper | Regional mainstream | Japanese / EN: No | No | Direct scraping | — | — | Medium / Phase 2 | Hyogo; Kansai; local government | High-value Japanese national, regional, business, technology, investigative, or perspective source. |

## Independent & Investigative Media

| Source | Organization type | Orientation | Language / English | Official status | Ingestion | RSS / feed page | YouTube | Priority / Phase | Topics | Value / access notes |
|---|---|---|---|---|---|---|---|---|---|---|
| [Bunshun Online (文春オンライン)](https://bunshun.jp/) | Magazine/digital | Tabloid/investigative | Japanese / EN: No | No | Direct scraping | — | — | High / Phase 2 | Political scandals; investigations; entertainment | High-value Japanese national, regional, business, technology, investigative, or perspective source. Paywall/member content; tabloid mix. |
| [Tansa](https://tansajp.org/) | Nonprofit investigative newsroom | Independent / investigative | Japanese / EN: No | No | Direct scraping | — | — | High / Phase 2 | Corporate accountability; environment; government | High-value Japanese national, regional, business, technology, investigative, or perspective source. Low volume, deep investigations. |

## Political / Ideological & YouTube Media

| Source | Organization type | Orientation | Language / English | Official status | Ingestion | RSS / feed page | YouTube | Priority / Phase | Topics | Value / access notes |
|---|---|---|---|---|---|---|---|---|---|---|
| [Asahi Shimbun (朝日新聞)](https://www.asahi.com/) | Newspaper | Liberal / center-left | Japanese / EN: Yes | No | Playwright | — | — | Critical / Phase 1 | Politics; society; investigations; world | High-value Japanese national, regional, business, technology, investigative, or perspective source. Paywall and robots/anti-bot. |
| [Sankei Shimbun (産経新聞)](https://www.sankei.com/) | Newspaper | Conservative / right-leaning | Japanese / EN: No | No | Playwright | — | — | Critical / Phase 1 | Politics; security; China; culture; opinion | High-value Japanese national, regional, business, technology, investigative, or perspective source. Robots/access limits. |
| [Yomiuri Shimbun (読売新聞)](https://www.yomiuri.co.jp/) | Newspaper | Conservative / center-right | Japanese / EN: Yes | No | Direct scraping | — | — | Critical / Phase 1 | Politics; society; world; economy | High-value Japanese national, regional, business, technology, investigative, or perspective source. Paywall/membership on some content. |
| [Japan Forward](https://japan-forward.com/) | English-language digital publication | Conservative / Sankei-affiliated | English / EN: Yes | No | Native RSS | https://japan-forward.com/feed/ | — | High / Phase 2 | Japan politics; security; culture; China | High-value Japanese national, regional, business, technology, investigative, or perspective source. Opinion/editorial framing. |
| [Mainichi Shimbun (毎日新聞)](https://mainichi.jp/) | Newspaper | Center-left / liberal-leaning | Japanese / EN: Yes | No | Direct scraping | — | — | High / Phase 2 | Politics; society; regional; world | High-value Japanese national, regional, business, technology, investigative, or perspective source. Metered/paywalled. |
| [Tokyo Shimbun (東京新聞)](https://www.tokyo-np.co.jp/) | Regional/national newspaper | Center-left / liberal-leaning | Japanese / EN: No | No | Direct scraping | — | — | High / Phase 2 | Tokyo; national politics; social issues | High-value Japanese national, regional, business, technology, investigative, or perspective source. Some paywall. |

## Business & Financial News

| Source | Organization type | Orientation | Language / English | Official status | Ingestion | RSS / feed page | YouTube | Priority / Phase | Topics | Value / access notes |
|---|---|---|---|---|---|---|---|---|---|---|
| [Nikkei (日本経済新聞)](https://www.nikkei.com/) | Business newspaper | Business-focused / market-oriented | Japanese / EN: Yes | No | Direct scraping | — | — | Critical / Phase 1 | Markets; companies; economy; policy; technology | High-value Japanese national, regional, business, technology, investigative, or perspective source. Strong paywall; licensed access preferable. |
| [Nikkei Asia](https://asia.nikkei.com/) | Regional business publication | Business-focused / mainstream | English / EN: Yes | No | Direct scraping | — | — | Critical / Phase 1 | Asia business; China; Japan; Southeast Asia; geopolitics | High-value Japanese national, regional, business, technology, investigative, or perspective source. Paywall. |
| [Toyo Keizai Online (東洋経済オンライン)](https://toyokeizai.net/) | Business magazine/digital | Business-focused | Japanese / EN: No | No | Direct scraping | — | — | High / Phase 2 | Economy; companies; policy; careers | High-value Japanese national, regional, business, technology, investigative, or perspective source. Some premium content. |
| [Diamond Online (ダイヤモンド・オンライン)](https://diamond.jp/) | Business magazine/digital | Business-focused | Japanese / EN: No | No | Direct scraping | — | — | Medium / Phase 2 | Business; management; economy; politics | High-value Japanese national, regional, business, technology, investigative, or perspective source. Paywall/premium content. |

## Defense, Military, Intelligence & Geopolitics

| Source | Organization type | Orientation | Language / English | Official status | Ingestion | RSS / feed page | YouTube | Priority / Phase | Topics | Value / access notes |
|---|---|---|---|---|---|---|---|---|---|---|
| [Okinawa Times (沖縄タイムス)](https://www.okinawatimes.co.jp/) | Regional newspaper | Regional / center-left perceived | Japanese / EN: No | No | Playwright | — | — | Critical / Phase 1 | Okinawa; U.S. bases; local politics; defense | High-value Japanese national, regional, business, technology, investigative, or perspective source. Robots/access restrictions and paywalled items. |
| [Ryukyu Shimpo (琉球新報)](https://ryukyushimpo.jp/) | Regional newspaper | Regional / center-left perceived | Japanese / EN: No | No | Native RSS | https://ryukyushimpo.jp/pages/entry-164983.html | — | Critical / Phase 1 | Okinawa; U.S. bases; politics; local society | High-value Japanese national, regional, business, technology, investigative, or perspective source. Exact feed endpoints should be harvested from landing page. |

## Technology & Cybersecurity

| Source | Organization type | Orientation | Language / English | Official status | Ingestion | RSS / feed page | YouTube | Priority / Phase | Topics | Value / access notes |
|---|---|---|---|---|---|---|---|---|---|---|
| [Security NEXT](https://www.security-next.com/) | Cybersecurity publication | Cybersecurity specialist | Japanese / EN: No | No | Direct scraping | — | — | Critical / Phase 1 | Breaches; vulnerabilities; security policy | High-value Japanese national, regional, business, technology, investigative, or perspective source. |
| [ITmedia](https://www.itmedia.co.jp/) | Technology publication | Technology specialist | Japanese / EN: No | No | Direct scraping | — | — | High / Phase 2 | Enterprise tech; AI; cybersecurity; electronics | High-value Japanese national, regional, business, technology, investigative, or perspective source. Multiple subsites. |
| [ScanNetSecurity](https://scan.netsecurity.ne.jp/) | Cybersecurity publication | Cybersecurity specialist | Japanese / EN: No | No | Direct scraping | — | — | High / Phase 2 | Cyber incidents; vulnerabilities; compliance | High-value Japanese national, regional, business, technology, investigative, or perspective source. Some member content. |

## Legislatures, Courts & Election Authorities

| Source | Organization type | Orientation | Language / English | Official status | Ingestion | RSS / feed page | YouTube | Priority / Phase | Topics | Value / access notes |
|---|---|---|---|---|---|---|---|---|---|---|
| [House of Councillors (参議院)](https://www.sangiin.go.jp/) | Legislature | Official | Japanese / EN: Yes | Yes - official Japanese government/institution | changedetection.io | — | — | Critical / Phase 1 | Bills; committees; plenary; records | Primary-source Japanese executive, legislative, legal, defense, security, or law-enforcement information. PDF/legacy HTML or decentralized subpages may require targeted monitors. |
| [House of Representatives (衆議院)](https://www.shugiin.go.jp/) | Legislature | Official | Japanese / EN: Yes | Yes - official Japanese government/institution | changedetection.io | — | — | Critical / Phase 1 | Bills; committees; plenary; records | Primary-source Japanese executive, legislative, legal, defense, security, or law-enforcement information. PDF/legacy HTML or decentralized subpages may require targeted monitors. |
| [Supreme Court of Japan / Courts](https://www.courts.go.jp/) | Court system | Official | Japanese / EN: Yes | Yes - official Japanese government/institution | changedetection.io | — | — | Critical / Phase 1 | Judgments; court administration; case information | Primary-source Japanese executive, legislative, legal, defense, security, or law-enforcement information. PDF/legacy HTML or decentralized subpages may require targeted monitors. |

## Government, Executive, Defense, Security & Law Enforcement

| Source | Organization type | Orientation | Language / English | Official status | Ingestion | RSS / feed page | YouTube | Priority / Phase | Topics | Value / access notes |
|---|---|---|---|---|---|---|---|---|---|---|
| [Cabinet Office (内閣府)](https://www.cao.go.jp/) | Government ministry/office | Official | Japanese / EN: Yes | Yes - official Japanese government/institution | Native RSS | https://www.cao.go.jp/rss/news.rdf | — | Critical / Phase 1 | Cabinet policy; economy; surveys; disaster policy | Primary-source Japanese executive, legislative, legal, defense, security, or law-enforcement information. PDF/legacy HTML or decentralized subpages may require targeted monitors. |
| [Cabinet Secretariat (内閣官房)](https://www.cas.go.jp/) | Executive secretariat | Official | Japanese / EN: Yes | Yes - official Japanese government/institution | changedetection.io | — | — | Critical / Phase 1 | National security; cabinet decisions; crisis response | Primary-source Japanese executive, legislative, legal, defense, security, or law-enforcement information. PDF/legacy HTML or decentralized subpages may require targeted monitors. |
| [Japan Air Self-Defense Force (航空自衛隊)](https://www.mod.go.jp/asdf/) | Military branch | Official | Japanese / EN: Yes | Yes - official Japanese government/institution | YouTube/yt-dlp | — | https://www.youtube.com/@JASDFchannel | Critical / Phase 1 | Air scrambles; exercises; aircraft | Primary-source Japanese executive, legislative, legal, defense, security, or law-enforcement information. PDF/legacy HTML or decentralized subpages may require targeted monitors. |
| [Japan Coast Guard (海上保安庁)](https://www.kaiho.mlit.go.jp/) | Coast guard | Official | Japanese / EN: Yes | Yes - official Japanese government/institution | changedetection.io | — | — | Critical / Phase 1 | Maritime incidents; Senkaku; navigation; rescues | Primary-source Japanese executive, legislative, legal, defense, security, or law-enforcement information. PDF/legacy HTML or decentralized subpages may require targeted monitors. |
| [Japan Joint Staff (統合幕僚監部)](https://www.mod.go.jp/js/) | Military command | Official | Japanese / EN: Yes | Yes - official Japanese government/institution | YouTube/yt-dlp | — | https://www.youtube.com/@jointstaffjapan | Critical / Phase 1 | Scrambles; exercises; ship/aircraft monitoring; operations | Primary-source Japanese executive, legislative, legal, defense, security, or law-enforcement information. PDF/legacy HTML or decentralized subpages may require targeted monitors. |
| [Japan Maritime Self-Defense Force (海上自衛隊)](https://www.mod.go.jp/msdf/) | Military branch | Official | Japanese / EN: Yes | Yes - official Japanese government/institution | YouTube/yt-dlp | — | https://www.youtube.com/@jmsdfmsopao | Critical / Phase 1 | Naval operations; exercises; ships; Indo-Pacific | Primary-source Japanese executive, legislative, legal, defense, security, or law-enforcement information. PDF/legacy HTML or decentralized subpages may require targeted monitors. |
| [Ministry of Defense (防衛省)](https://www.mod.go.jp/) | Defense ministry | Official | Japanese / EN: Yes | Yes - official Japanese government/institution | Native RSS | https://www.mod.go.jp/j/press/news/ | https://www.youtube.com/@modchannel | Critical / Phase 1 | Defense policy; procurement; operations; China/North Korea | Primary-source Japanese executive, legislative, legal, defense, security, or law-enforcement information. PDF/legacy HTML or decentralized subpages may require targeted monitors. |
| [Ministry of Foreign Affairs of Japan (MOFA)](https://www.mofa.go.jp/) | Foreign ministry | Official | Japanese / EN: Yes | Yes - official Japanese government/institution | changedetection.io | — | — | Critical / Phase 1 | Diplomacy; treaties; sanctions; statements | Primary-source Japanese executive, legislative, legal, defense, security, or law-enforcement information. PDF/legacy HTML or decentralized subpages may require targeted monitors. |
| [Ministry of Internal Affairs and Communications (MIC)](https://www.soumu.go.jp/) | Government ministry | Official | Japanese / EN: Yes | Yes - official Japanese government/institution | changedetection.io | — | — | Critical / Phase 1 | Elections; telecom; local government; statistics | Primary-source Japanese executive, legislative, legal, defense, security, or law-enforcement information. PDF/legacy HTML or decentralized subpages may require targeted monitors. |
| [Prime Minister's Office (Kantei / 首相官邸)](https://www.kantei.go.jp/) | Executive office | Official | Japanese / EN: Yes | Yes - official Japanese government/institution | Native RSS | https://www.kantei.go.jp/jp/rss/ | — | Critical / Phase 1 | Prime minister; cabinet; speeches; policy | Primary-source Japanese executive, legislative, legal, defense, security, or law-enforcement information. PDF/legacy HTML or decentralized subpages may require targeted monitors. |
| [Acquisition, Technology & Logistics Agency (ATLA)](https://www.mod.go.jp/atla/) | Defense acquisition agency | Official | Japanese / EN: Yes | Yes - official Japanese government/institution | changedetection.io | — | — | High / Phase 2 | Defense procurement; R&D; acquisition | Primary-source Japanese executive, legislative, legal, defense, security, or law-enforcement information. PDF/legacy HTML or decentralized subpages may require targeted monitors. |
| [Japan Ground Self-Defense Force (陸上自衛隊)](https://www.mod.go.jp/gsdf/) | Military branch | Official | Japanese / EN: Yes | Yes - official Japanese government/institution | YouTube/yt-dlp | — | https://www.youtube.com/@JGSDFchannel | High / Phase 2 | Exercises; deployments; units | Primary-source Japanese executive, legislative, legal, defense, security, or law-enforcement information. PDF/legacy HTML or decentralized subpages may require targeted monitors. |
| [National Police Agency (警察庁)](https://www.npa.go.jp/) | Police agency | Official | Japanese / EN: Yes | Yes - official Japanese government/institution | Native RSS | https://www.npa.go.jp/news/rss.html | — | High / Phase 2 | Crime; cyber; public safety; statistics | Primary-source Japanese executive, legislative, legal, defense, security, or law-enforcement information. PDF/legacy HTML or decentralized subpages may require targeted monitors. |
| [Public Security Intelligence Agency (公安調査庁)](https://www.moj.go.jp/psia/) | Security/intelligence agency | Official | Japanese / EN: Yes | Yes - official Japanese government/institution | changedetection.io | — | — | High / Phase 2 | Security threats; economic security; extremism | Primary-source Japanese executive, legislative, legal, defense, security, or law-enforcement information. PDF/legacy HTML or decentralized subpages may require targeted monitors. |

## Think Tanks, Research Institutes & Universities

| Source | Organization type | Orientation | Language / English | Official status | Ingestion | RSS / feed page | YouTube | Priority / Phase | Topics | Value / access notes |
|---|---|---|---|---|---|---|---|---|---|---|
| [National Institute for Defense Studies (NIDS)](https://www.nids.mod.go.jp/) | Defense research institute | Official research | Japanese / EN: Yes | Government-affiliated/official research | changedetection.io | — | — | Critical / Phase 1 | Foreign policy; defense; China; Korea; economic security; Indo-Pacific | High-value monitoring source for the platform. PDF-heavy or low-frequency institutional publishing. |
| [IDE-JETRO](https://www.ide.go.jp/English/) | Research institute | Government-affiliated research | Japanese / EN: Yes | Government-affiliated/official research | Direct scraping | — | — | High / Phase 2 | Foreign policy; defense; China; Korea; economic security; Indo-Pacific | High-value monitoring source for the platform. PDF-heavy or low-frequency institutional publishing. |
| [Institute of Geoeconomics (IOG)](https://instituteofgeoeconomics.org/) | Think tank | Policy research | Japanese / EN: Yes | No | Direct scraping | — | — | High / Phase 2 | Foreign policy; defense; China; Korea; economic security; Indo-Pacific | High-value monitoring source for the platform. PDF-heavy or low-frequency institutional publishing. |
| [Japan Institute of International Affairs (JIIA)](https://www.jiia.or.jp/) | Think tank | Mainstream / policy establishment | Japanese / EN: Yes | No | Direct scraping | — | — | High / Phase 2 | Foreign policy; defense; China; Korea; economic security; Indo-Pacific | High-value monitoring source for the platform. PDF-heavy or low-frequency institutional publishing. |
| [Sasakawa Peace Foundation](https://www.spf.org/) | Foundation / think tank | Policy research | Japanese / EN: Yes | No | Direct scraping | — | — | High / Phase 2 | Foreign policy; defense; China; Korea; economic security; Indo-Pacific | High-value monitoring source for the platform. PDF-heavy or low-frequency institutional publishing. |
| [GRIPS Alliance / National Graduate Institute for Policy Studies](https://www.grips.ac.jp/en/) | University/policy center | Academic | Japanese / EN: Yes | No | changedetection.io | — | — | Medium / Phase 2 | Foreign policy; defense; China; Korea; economic security; Indo-Pacific | High-value monitoring source for the platform. PDF-heavy or low-frequency institutional publishing. |
| [Research Institute for Peace and Security (RIPS)](https://www.rips.or.jp/english/) | Think tank | Policy research | Japanese / EN: Yes | No | changedetection.io | — | — | Medium / Phase 2 | Foreign policy; defense; China; Korea; economic security; Indo-Pacific | High-value monitoring source for the platform. PDF-heavy or low-frequency institutional publishing. |
| [University of Tokyo ROLES](https://roles.rcast.u-tokyo.ac.jp/) | University policy center | Academic | Japanese / EN: Yes | No | changedetection.io | — | — | Medium / Phase 2 | Foreign policy; defense; China; Korea; economic security; Indo-Pacific | High-value monitoring source for the platform. PDF-heavy or low-frequency institutional publishing. |

## Other High-Value Sources

| Source | Organization type | Orientation | Language / English | Official status | Ingestion | RSS / feed page | YouTube | Priority / Phase | Topics | Value / access notes |
|---|---|---|---|---|---|---|---|---|---|---|
| [JBpress](https://jbpress.ismedia.jp/) | Digital analysis outlet | Center-right / security-focused | Japanese / EN: No | No | Direct scraping | — | — | High / Phase 2 | Security; China; economy; politics | High-value Japanese national, regional, business, technology, investigative, or perspective source. Opinion-heavy; some member content. |

# Taiwan

## Major National / Political News

| Source | Organization type | Orientation | Language / English | Official status | Ingestion | RSS / feed page | YouTube | Priority / Phase | Topics | Value / access notes |
|---|---|---|---|---|---|---|---|---|---|---|
| [Public Television Service (公視 / PTS)](https://news.pts.org.tw/) | Public broadcaster | Public broadcaster | Traditional Chinese / EN: Limited | No | Native RSS | https://about.pts.org.tw/rss/index.html | — | Critical / Phase 1 | Politics; society; public affairs; local | High-value Taiwan national, cross-strait, investigative, technology, business, or political-perspective source. Harvest exact feed URLs from RSS page. |
| [United Daily News (聯合新聞網 / UDN)](https://udn.com/) | Newspaper/digital network | Center-right / pan-blue perceived | Traditional Chinese / EN: Limited | No | Direct scraping | — | — | Critical / Phase 1 | Politics; cross-strait; economy; society | High-value Taiwan national, cross-strait, investigative, technology, business, or political-perspective source. Dynamic pages/ads. |
| [Formosa TV News (民視新聞)](https://www.ftvnews.com.tw/) | Television news | Pan-green perceived | Traditional Chinese / EN: Limited | No | YouTube/yt-dlp | — | https://www.youtube.com/@FTVNews | High / Phase 2 | Politics; elections; society; live news | High-value Taiwan national, cross-strait, investigative, technology, business, or political-perspective source. Video-heavy. |
| [SET News (三立新聞網)](https://www.setn.com/) | Television/digital news | Pan-green perceived | Traditional Chinese / EN: Limited | No | YouTube/yt-dlp | — | https://www.youtube.com/@setn | High / Phase 2 | Politics; elections; breaking; society | High-value Taiwan national, cross-strait, investigative, technology, business, or political-perspective source. High volume/sensational elements; deduplicate. |
| [TVBS News](https://news.tvbs.com.tw/) | Television/digital news | Center-right / pan-blue perceived | Traditional Chinese / EN: Limited | No | YouTube/yt-dlp | — | https://www.youtube.com/@TVBSNEWS01 | High / Phase 2 | Politics; elections; breaking; society | High-value Taiwan national, cross-strait, investigative, technology, business, or political-perspective source. High-volume video. |
| [Taipei Times](https://www.taipeitimes.com/) | English-language newspaper | Pan-green / liberal-leaning perceived | English / EN: Yes | No | Native RSS | https://www.taipeitimes.com/xml/index.rss | — | High / Phase 1 | Politics; defense; cross-strait; society | High-value Taiwan national, cross-strait, investigative, technology, business, or political-perspective source. Feed health should be checked. |
| [Taiwan News](https://www.taiwannews.com.tw/) | English-language digital outlet | Taiwan-focused / generally pro-Taiwan | English / EN: Yes | No | Direct scraping | — | — | High / Phase 2 | Politics; defense; China; society | High-value Taiwan national, cross-strait, investigative, technology, business, or political-perspective source. Site structure changes periodically. |
| [TaiwanPlus](https://www.taiwanplus.com/) | Publicly funded international media | Publicly funded / international-facing | English / EN: Yes | No | YouTube/yt-dlp | — | https://www.youtube.com/@TaiwanPlus | High / Phase 2 | Taiwan politics; China; Indo-Pacific; culture | High-value Taiwan national, cross-strait, investigative, technology, business, or political-perspective source. Video-first; site may be JS-heavy. |
| [EBC News (東森新聞)](https://news.ebc.net.tw/) | Television/digital news | Commercial mainstream | Traditional Chinese / EN: Limited | No | YouTube/yt-dlp | — | https://www.youtube.com/@newsebc | Medium / Phase 2 | Breaking; politics; society; business | High-value Taiwan national, cross-strait, investigative, technology, business, or political-perspective source. Site/video overlap. |

## Regional & Local News

| Source | Organization type | Orientation | Language / English | Official status | Ingestion | RSS / feed page | YouTube | Priority / Phase | Topics | Value / access notes |
|---|---|---|---|---|---|---|---|---|---|---|
| [Central News Agency (中央通訊社 / CNA)](https://www.cna.com.tw/) | National news agency | Mainstream / national wire | Traditional Chinese / EN: Yes | No | Native RSS | https://feeds.feedburner.com/rsscna/politics | — | Critical / Phase 1 | Politics; cross-strait; world; economy; technology | High-value Taiwan national, cross-strait, investigative, technology, business, or political-perspective source. RSS terms restrict noncommercial reuse; use internally with attribution. |

## Independent & Investigative Media

| Source | Organization type | Orientation | Language / English | Official status | Ingestion | RSS / feed page | YouTube | Priority / Phase | Topics | Value / access notes |
|---|---|---|---|---|---|---|---|---|---|---|
| [The Reporter (報導者)](https://www.twreporter.org/) | Nonprofit investigative newsroom | Independent / nonprofit | Traditional Chinese / EN: Limited | No | Direct scraping | — | — | Critical / Phase 1 | Investigations; labor; human rights; environment | High-value Taiwan national, cross-strait, investigative, technology, business, or political-perspective source. Low volume/high value; preserve multimedia/data. |
| [Mirror Media (鏡週刊 / 鏡新聞)](https://www.mirrormedia.mg/) | Magazine/digital/broadcast | Independent / investigative-popular | Traditional Chinese / EN: Limited | No | Direct scraping | — | — | High / Phase 2 | Politics; investigations; business; society | High-value Taiwan national, cross-strait, investigative, technology, business, or political-perspective source. Some tabloid/lifestyle mix. |
| [Storm Media (風傳媒)](https://www.storm.mg/) | Digital news outlet | Mixed / pluralist digital outlet | Traditional Chinese / EN: Limited | No | Direct scraping | — | — | High / Phase 2 | Politics; opinion; business; cross-strait | High-value Taiwan national, cross-strait, investigative, technology, business, or political-perspective source. Mix reporting/opinion. |
| [New Bloom Magazine](https://newbloommag.net/) | Independent digital magazine | Progressive / left-leaning | English / EN: Limited | No | Native RSS | https://newbloommag.net/feed/ | — | Medium / Phase 2 | Taiwan politics; social movements; China | High-value Taiwan national, cross-strait, investigative, technology, business, or political-perspective source. Analysis/opinion heavy. |

## Political / Ideological & YouTube Media

| Source | Organization type | Orientation | Language / English | Official status | Ingestion | RSS / feed page | YouTube | Priority / Phase | Topics | Value / access notes |
|---|---|---|---|---|---|---|---|---|---|---|
| [China Times (中國時報)](https://www.chinatimes.com/) | Newspaper | Pan-blue / China-friendly perceived | Traditional Chinese / EN: Limited | No | Direct scraping | — | — | Critical / Phase 1 | Politics; cross-strait; society; business | High-value Taiwan national, cross-strait, investigative, technology, business, or political-perspective source. Dynamic site. |
| [Liberty Times (自由時報)](https://www.ltn.com.tw/) | Newspaper | Pan-green / Taiwan-localist leaning | Traditional Chinese / EN: Limited | No | Native RSS | https://news.ltn.com.tw/rss/all.xml | — | Critical / Phase 1 | Politics; defense; local; cross-strait; world | High-value Taiwan national, cross-strait, investigative, technology, business, or political-perspective source. RSS terms emphasize noncommercial use/attribution. |

## Business & Financial News

| Source | Organization type | Orientation | Language / English | Official status | Ingestion | RSS / feed page | YouTube | Priority / Phase | Topics | Value / access notes |
|---|---|---|---|---|---|---|---|---|---|---|
| [CommonWealth Magazine (天下雜誌)](https://www.cw.com.tw/) | Business magazine | Business-focused / mainstream | Traditional Chinese / EN: Limited | No | Direct scraping | — | — | High / Phase 2 | Economy; companies; policy; society | High-value Taiwan national, cross-strait, investigative, technology, business, or political-perspective source. Premium paywall. |

## Technology & Cybersecurity

| Source | Organization type | Orientation | Language / English | Official status | Ingestion | RSS / feed page | YouTube | Priority / Phase | Topics | Value / access notes |
|---|---|---|---|---|---|---|---|---|---|---|
| [Administration for Cyber Security, MODA](https://moda.gov.tw/ACS/) | Cybersecurity agency | Official | Traditional Chinese / EN: Limited | Yes - official Taiwan government/institution | changedetection.io | — | — | Critical / Phase 1 | Cybersecurity; incidents; policy; resilience | Primary-source Taiwan executive, legislative, election, defense, cross-strait, security, or legal information. Target specific release/index pages; some sites are dynamic. |
| [DigiTimes](https://www.digitimes.com/) | Technology/business publication | Technology industry specialist | Traditional Chinese / EN: Yes | No | Direct scraping | — | — | Critical / Phase 1 | Semiconductors; supply chains; electronics; AI | High-value Taiwan national, cross-strait, investigative, technology, business, or political-perspective source. Subscription/paywall; licensed access may be needed. |
| [iThome](https://www.ithome.com.tw/) | Technology publication | Technology specialist | Traditional Chinese / EN: Limited | No | Direct scraping | — | — | Critical / Phase 1 | Enterprise IT; cybersecurity; cloud; AI | High-value Taiwan national, cross-strait, investigative, technology, business, or political-perspective source. |
| [National Chung-Shan Institute of Science and Technology (NCSIST)](https://www.ncsist.org.tw/) | Defense research organization | Official | Traditional Chinese / EN: Limited | Yes - official Taiwan government/institution | changedetection.io | — | — | High / Phase 2 | Defense technology; missiles; drones; R&D | Primary-source Taiwan executive, legislative, election, defense, cross-strait, security, or legal information. Target specific release/index pages; some sites are dynamic. |
| [TechNews 科技新報](https://technews.tw/) | Technology publication | Technology specialist | Traditional Chinese / EN: Limited | No | Native RSS | https://technews.tw/feed/ | — | High / Phase 1 | Semiconductors; AI; energy; technology | High-value Taiwan national, cross-strait, investigative, technology, business, or political-perspective source. |
| [Inside](https://www.inside.com.tw/) | Technology publication | Technology specialist | Traditional Chinese / EN: Limited | No | Direct scraping | — | — | Medium / Phase 2 | Startups; internet; AI; digital policy | High-value Taiwan national, cross-strait, investigative, technology, business, or political-perspective source. No broad RSS verified. |

## Legislatures, Courts & Election Authorities

| Source | Organization type | Orientation | Language / English | Official status | Ingestion | RSS / feed page | YouTube | Priority / Phase | Topics | Value / access notes |
|---|---|---|---|---|---|---|---|---|---|---|
| [Central Election Commission (中央選舉委員會)](https://www.cec.gov.tw/) | Election commission | Official | Traditional Chinese / EN: Limited | Yes - official Taiwan government/institution | changedetection.io | — | — | Critical / Phase 1 | Elections; referendums; regulations; results | Primary-source Taiwan executive, legislative, election, defense, cross-strait, security, or legal information. Target specific release/index pages; some sites are dynamic. |
| [Constitutional Court (憲法法庭)](https://cons.judicial.gov.tw/) | Constitutional court | Official | Traditional Chinese / EN: Limited | Yes - official Taiwan government/institution | changedetection.io | — | — | Critical / Phase 1 | Constitutional judgments; hearings; petitions | Primary-source Taiwan executive, legislative, election, defense, cross-strait, security, or legal information. Target specific release/index pages; some sites are dynamic. |
| [Judicial Yuan (司法院)](https://www.judicial.gov.tw/) | Judiciary | Official | Traditional Chinese / EN: Limited | Yes - official Taiwan government/institution | changedetection.io | — | — | Critical / Phase 1 | Court administration; judgments; judicial news | Primary-source Taiwan executive, legislative, election, defense, cross-strait, security, or legal information. Target specific release/index pages; some sites are dynamic. |
| [Legislative Yuan (立法院)](https://www.ly.gov.tw/) | Legislature | Official | Traditional Chinese / EN: Limited | Yes - official Taiwan government/institution | changedetection.io | — | — | Critical / Phase 1 | Bills; committees; hearings; parliamentary news | Primary-source Taiwan executive, legislative, election, defense, cross-strait, security, or legal information. Target specific release/index pages; some sites are dynamic. |

## Government, Executive, Defense, Security & Law Enforcement

| Source | Organization type | Orientation | Language / English | Official status | Ingestion | RSS / feed page | YouTube | Priority / Phase | Topics | Value / access notes |
|---|---|---|---|---|---|---|---|---|---|---|
| [Coast Guard Administration (海巡署)](https://www.cga.gov.tw/) | Coast guard | Official | Traditional Chinese / EN: Limited | Yes - official Taiwan government/institution | changedetection.io | — | — | Critical / Phase 1 | Maritime incidents; gray-zone activity; patrols | Primary-source Taiwan executive, legislative, election, defense, cross-strait, security, or legal information. Target specific release/index pages; some sites are dynamic. |
| [Executive Yuan (行政院)](https://www.ey.gov.tw/) | Executive cabinet | Official | Traditional Chinese / EN: Limited | Yes - official Taiwan government/institution | changedetection.io | — | — | Critical / Phase 1 | Cabinet policy; press releases; regulations | Primary-source Taiwan executive, legislative, election, defense, cross-strait, security, or legal information. Target specific release/index pages; some sites are dynamic. |
| [Mainland Affairs Council (大陸委員會)](https://www.mac.gov.tw/) | Cross-strait affairs agency | Official | Traditional Chinese / EN: Yes | Yes - official Taiwan government/institution | Native RSS | https://www.mac.gov.tw/RSS.aspx?n=1FDDB0BEA67BC1D9 | — | Critical / Phase 1 | Cross-strait relations; China policy; statistics | Primary-source Taiwan executive, legislative, election, defense, cross-strait, security, or legal information. Target specific release/index pages; some sites are dynamic. |
| [Ministry of Foreign Affairs (外交部)](https://www.mofa.gov.tw/) | Foreign ministry | Official | Traditional Chinese / EN: Yes | Yes - official Taiwan government/institution | Native RSS | https://www.mofa.gov.tw/RSS.aspx | — | Critical / Phase 1 | Diplomacy; statements; sanctions; international relations | Primary-source Taiwan executive, legislative, election, defense, cross-strait, security, or legal information. Target specific release/index pages; some sites are dynamic. |
| [Ministry of National Defense (國防部)](https://www.mnd.gov.tw/) | Defense ministry | Official | Traditional Chinese / EN: Limited | Yes - official Taiwan government/institution | changedetection.io | — | — | Critical / Phase 1 | PLA activity; defense policy; exercises; procurement | Primary-source Taiwan executive, legislative, election, defense, cross-strait, security, or legal information. Target specific release/index pages; some sites are dynamic. |
| [Office of the President, Republic of China (Taiwan)](https://www.president.gov.tw/) | Executive office | Official | Traditional Chinese / EN: Yes | Yes - official Taiwan government/institution | Native RSS | https://www.president.gov.tw/Page/23 | — | Critical / Phase 1 | Presidential statements; speeches; national security; appointments | Primary-source Taiwan executive, legislative, election, defense, cross-strait, security, or legal information. Target specific release/index pages; some sites are dynamic. |
| [National Police Agency (警政署)](https://www.npa.gov.tw/) | Police agency | Official | Traditional Chinese / EN: Limited | Yes - official Taiwan government/institution | changedetection.io | — | — | High / Phase 2 | Crime; public safety; cybercrime | Primary-source Taiwan executive, legislative, election, defense, cross-strait, security, or legal information. Target specific release/index pages; some sites are dynamic. |
| [National Security Bureau (國家安全局)](https://www.nsb.gov.tw/) | Intelligence agency | Official | Traditional Chinese / EN: Limited | Yes - official Taiwan government/institution | changedetection.io | — | — | High / Phase 2 | National security; intelligence; public reports | Primary-source Taiwan executive, legislative, election, defense, cross-strait, security, or legal information. Target specific release/index pages; some sites are dynamic. |

## Think Tanks, Research Institutes & Universities

| Source | Organization type | Orientation | Language / English | Official status | Ingestion | RSS / feed page | YouTube | Priority / Phase | Topics | Value / access notes |
|---|---|---|---|---|---|---|---|---|---|---|
| [Institute for National Defense and Security Research (INDSR)](https://indsr.org.tw/) | Defense think tank | Government-funded / defense research | Traditional Chinese / EN: Yes | Government-funded research | Direct scraping | — | — | Critical / Phase 1 | PLA; defense; China; gray-zone operations | High-value monitoring source for the platform. Reports/PDFs; low-volume institutional output. |
| [Doublethink Lab](https://doublethinklab.org/) | Research nonprofit | Independent / civil society | Traditional Chinese / EN: Yes | No | Direct scraping | — | — | High / Phase 2 | Information operations; China influence; disinformation | High-value monitoring source for the platform. |
| [Institute of International Relations, NCCU](https://iir.nccu.edu.tw/) | University research center | Academic | Traditional Chinese / EN: Yes | No | changedetection.io | — | — | High / Phase 2 | China; cross-strait; international relations | High-value monitoring source for the platform. Reports/PDFs; low-volume institutional output. |
| [Prospect Foundation](https://www.pf.org.tw/) | Think tank | Policy institute / Taiwan-centric | Traditional Chinese / EN: Yes | No | Direct scraping | — | — | High / Phase 2 | Cross-strait; Indo-Pacific; foreign policy | High-value monitoring source for the platform. |
| [Taiwan FactCheck Center](https://tfc-taiwan.org.tw/) | Nonprofit fact-checker | Nonpartisan / fact-checking | Traditional Chinese / EN: Yes | No | Direct scraping | — | — | High / Phase 2 | Misinformation; elections; China narratives | High-value monitoring source for the platform. |
| [Academia Sinica](https://www.sinica.edu.tw/en) | National research academy | Academic / public research | Traditional Chinese / EN: Yes | Government-funded research | Direct scraping | — | — | Medium / Phase 2 | China; political science; economics; social science | High-value monitoring source for the platform. |
| [Taiwan-Asia Exchange Foundation](https://www.taef.org/) | Foundation / think tank | Policy institute | Traditional Chinese / EN: Yes | No | Direct scraping | — | — | Medium / Phase 2 | New Southbound Policy; Southeast Asia; regional affairs | High-value monitoring source for the platform. |

# China

## Major National / Political News

| Source | Organization type | Orientation | Language / English | Official status | Ingestion | RSS / feed page | YouTube | Priority / Phase | Topics | Value / access notes |
|---|---|---|---|---|---|---|---|---|---|---|
| [CCTV News / 央视新闻](https://news.cctv.com/) | State broadcaster | State media / official | Simplified Chinese / EN: Limited | State/official media | YouTube/yt-dlp | — | https://www.youtube.com/@CCTVVideoNewsAgency | Critical / Phase 1 | Breaking; leadership; military; society | High-value Chinese state, commercial, business, technology, cyber, or independent monitoring source. Domestic video pages can be difficult. |
| [CGTN](https://www.cgtn.com/) | State international broadcaster | State media / official | English/Chinese / EN: Yes | State/official media | YouTube/yt-dlp | — | https://www.youtube.com/@cgtn | Critical / Phase 1 | China; world; foreign policy; economy | High-value Chinese state, commercial, business, technology, cyber, or independent monitoring source. Video-first; site may be JS-heavy. |
| [Global Times (环球时报)](https://www.globaltimes.cn/) | Party-affiliated tabloid/newspaper | Nationalist / CCP-affiliated | Simplified Chinese / EN: Yes | No | Direct scraping | — | https://www.youtube.com/@globaltimes | Critical / Phase 1 | Foreign policy; U.S.; Taiwan; nationalism; security | High-value Chinese state, commercial, business, technology, cyber, or independent monitoring source. Distinguish rhetoric/commentary from formal policy. |
| [People's Daily (人民日报)](http://www.people.com.cn/) | Party newspaper | CCP official party media | Simplified Chinese / EN: Limited | State/official media | Direct scraping | — | — | Critical / Phase 1 | Party policy; leadership; ideology; domestic affairs | High-value Chinese state, commercial, business, technology, cyber, or independent monitoring source. Legacy structures; versioning important for edits/deletions. |
| [Xinhua News Agency (新华社)](https://www.news.cn/) | State news agency | State media / official | Simplified Chinese / EN: Yes | State/official media | YouTube/yt-dlp | — | https://www.youtube.com/@NewChinaTV | Critical / Phase 1 | Politics; economy; foreign affairs; official statements | High-value Chinese state, commercial, business, technology, cyber, or independent monitoring source. Domestic site may limit scraping; English/video alternate paths. |
| [China Daily](https://www.chinadaily.com.cn/) | State-owned newspaper | State media / official-aligned | English/Chinese / EN: Yes | State/official media | YouTube/yt-dlp | — | https://www.youtube.com/@chinadaily | High / Phase 1 | China policy; economy; diplomacy; commentary | High-value Chinese state, commercial, business, technology, cyber, or independent monitoring source. |
| [The Beijing News (新京报)](https://www.bjnews.com.cn/) | Newspaper/digital | Commercial mainstream | Simplified Chinese / EN: Limited | No | Direct scraping | — | — | High / Phase 2 | Breaking; investigations; society; politics | High-value Chinese state, commercial, business, technology, cyber, or independent monitoring source. |
| [The Paper (澎湃新闻)](https://www.thepaper.cn/) | Digital news outlet | Commercial mainstream under Chinese media system | Simplified Chinese / EN: Limited | No | Playwright | — | — | High / Phase 1 | Politics; society; investigations; culture | High-value Chinese state, commercial, business, technology, cyber, or independent monitoring source. JavaScript-heavy/anti-bot. |

## Regional & Local News

| Source | Organization type | Orientation | Language / English | Official status | Ingestion | RSS / feed page | YouTube | Priority / Phase | Topics | Value / access notes |
|---|---|---|---|---|---|---|---|---|---|---|
| [China News Service (中国新闻网)](https://www.chinanews.com.cn/) | State news agency | State media | Simplified Chinese / EN: Limited | State/official media | Direct scraping | — | — | High / Phase 1 | Breaking; domestic; overseas Chinese; world | High-value Chinese state, commercial, business, technology, cyber, or independent monitoring source. |

## Independent & Investigative Media

| Source | Organization type | Orientation | Language / English | Official status | Ingestion | RSS / feed page | YouTube | Priority / Phase | Topics | Value / access notes |
|---|---|---|---|---|---|---|---|---|---|---|
| [China Digital Times](https://chinadigitaltimes.net/) | Independent overseas media/research | Independent / critical of CCP censorship | English/Chinese / EN: Yes | No | Native RSS | https://chinadigitaltimes.net/feed/ | — | Critical / Phase 1 | Censorship; propaganda; politics; social media | High-value Chinese state, commercial, business, technology, cyber, or independent monitoring source. Blocked in mainland China. |
| [Southern Weekly (南方周末)](https://www.infzm.com/) | Weekly newspaper | Liberal-leaning historical reputation within censorship constraints | Simplified Chinese / EN: Limited | No | Direct scraping | — | — | High / Phase 2 | Investigations; society; politics; commentary | High-value Chinese state, commercial, business, technology, cyber, or independent monitoring source. Censorship constraints; paywall may apply. |
| [What's on Weibo](https://www.whatsonweibo.com/) | Independent media analysis | Independent | English/Chinese / EN: Yes | No | Native RSS | https://www.whatsonweibo.com/feed/ | — | High / Phase 1 | Chinese social media; trends; narratives | High-value Chinese state, commercial, business, technology, cyber, or independent monitoring source. Curated/interpretive. |

## Business & Financial News

| Source | Organization type | Orientation | Language / English | Official status | Ingestion | RSS / feed page | YouTube | Priority / Phase | Topics | Value / access notes |
|---|---|---|---|---|---|---|---|---|---|---|
| [Caixin (财新)](https://www.caixin.com/) | Business/investigative media | Market-oriented / professional | Simplified Chinese / EN: Yes | No | Direct scraping | — | — | Critical / Phase 1 | Economy; finance; investigations; policy | High-value Chinese state, commercial, business, technology, cyber, or independent monitoring source. Strong paywall; subscription/session needed. |
| [Caijing (财经)](https://www.caijing.com.cn/) | Business magazine | Business-focused | Simplified Chinese / EN: Limited | No | Direct scraping | — | — | High / Phase 2 | Finance; economy; policy; companies | High-value Chinese state, commercial, business, technology, cyber, or independent monitoring source. Some premium content. |
| [Economic Daily (经济日报)](http://www.ce.cn/) | State economic newspaper | State media | Simplified Chinese / EN: Limited | State/official media | Direct scraping | — | — | High / Phase 2 | Economy; industrial policy; markets | High-value Chinese state, commercial, business, technology, cyber, or independent monitoring source. Legacy site. |
| [Jiemian News (界面新闻)](https://www.jiemian.com/) | Digital business/news outlet | Commercial mainstream | Simplified Chinese / EN: Limited | No | Playwright | — | — | High / Phase 2 | Business; companies; economy; politics | High-value Chinese state, commercial, business, technology, cyber, or independent monitoring source. JS-heavy. |
| [National Development and Reform Commission (国家发展改革委)](https://www.ndrc.gov.cn/) | Economic planning agency | Official | Simplified Chinese / EN: Limited | Yes - official PRC government/institution | changedetection.io | — | — | High / Phase 2 | Industrial policy; energy; prices; economic planning | Primary-source PRC government, legal, economic, security, Taiwan-policy, or maritime information. Pages may be updated/removed; preserve versions and retrieval timestamps. Access may vary by region. |
| [State Administration for Market Regulation](https://www.samr.gov.cn/) | Regulator | Official | Simplified Chinese / EN: Limited | Yes - official PRC government/institution | changedetection.io | — | — | High / Phase 2 | Antitrust; market regulation; corporate enforcement | Primary-source PRC government, legal, economic, security, Taiwan-policy, or maritime information. Pages may be updated/removed; preserve versions and retrieval timestamps. Access may vary by region. |
| [Yicai / First Financial (第一财经)](https://www.yicai.com/) | Business media | Business-focused | Simplified Chinese / EN: Limited | No | Direct scraping | — | — | High / Phase 1 | Markets; economy; companies; policy | High-value Chinese state, commercial, business, technology, cyber, or independent monitoring source. Dynamic pages. |

## Defense, Military, Intelligence & Geopolitics

| Source | Organization type | Orientation | Language / English | Official status | Ingestion | RSS / feed page | YouTube | Priority / Phase | Topics | Value / access notes |
|---|---|---|---|---|---|---|---|---|---|---|
| [PLA Daily / China Military Online (解放军报/中国军网)](http://www.81.cn/) | Military newspaper | Official PLA media | Simplified Chinese / EN: Limited | State/official media | Direct scraping | — | — | Critical / Phase 1 | PLA; exercises; doctrine; personnel; weapons | High-value Chinese state, commercial, business, technology, cyber, or independent monitoring source. Archive snapshots; content/site can change. |

## Technology & Cybersecurity

| Source | Organization type | Orientation | Language / English | Official status | Ingestion | RSS / feed page | YouTube | Priority / Phase | Topics | Value / access notes |
|---|---|---|---|---|---|---|---|---|---|---|
| [Cyberspace Administration of China (国家互联网信息办公室)](https://www.cac.gov.cn/) | Cyber/internet regulator | Official | Simplified Chinese / EN: Limited | Yes - official PRC government/institution | changedetection.io | — | — | Critical / Phase 1 | Internet regulation; censorship; data; AI rules | Primary-source PRC government, legal, economic, security, Taiwan-policy, or maritime information. Pages may be updated/removed; preserve versions and retrieval timestamps. Access may vary by region. |
| [FreeBuf](https://www.freebuf.com/) | Cybersecurity publication/community | Cybersecurity specialist | Simplified Chinese / EN: Limited | No | Direct scraping | — | — | Critical / Phase 1 | Cybersecurity; vulnerabilities; threat research | High-value Chinese state, commercial, business, technology, cyber, or independent monitoring source. Community content quality varies. |
| [36Kr (36氪)](https://36kr.com/) | Technology/business media | Technology/startup specialist | Simplified Chinese / EN: Limited | No | Playwright | — | — | High / Phase 1 | Startups; venture capital; AI; technology | High-value Chinese state, commercial, business, technology, cyber, or independent monitoring source. JS-heavy/app-centric; anti-bot possible. |
| [Anquanke (安全客)](https://www.anquanke.com/) | Cybersecurity publication/community | Cybersecurity specialist | Simplified Chinese / EN: Limited | No | Direct scraping | — | — | High / Phase 2 | Cyber threats; vulnerabilities; security research | High-value Chinese state, commercial, business, technology, cyber, or independent monitoring source. Community/vendor content mix. |
| [LatePost (晚点)](https://www.latepost.com/) | Technology/business media | Technology/business specialist | Simplified Chinese / EN: Limited | No | Direct scraping | — | — | High / Phase 2 | Technology companies; business strategy; China internet | High-value Chinese state, commercial, business, technology, cyber, or independent monitoring source. Some subscription/app-first content. |
| [Huxiu (虎嗅)](https://www.huxiu.com/) | Technology/business commentary | Independent commercial / commentary | Simplified Chinese / EN: Limited | No | Playwright | — | — | Medium / Phase 2 | Technology; business; internet; policy | High-value Chinese state, commercial, business, technology, cyber, or independent monitoring source. Membership content; JS-heavy. |
| [TMTPost (钛媒体)](https://www.tmtpost.com/) | Technology/business media | Technology specialist | Simplified Chinese / EN: Limited | No | Direct scraping | — | — | Medium / Phase 2 | Tech; AI; startups; business | High-value Chinese state, commercial, business, technology, cyber, or independent monitoring source. Some premium content. |

## Legislatures, Courts & Election Authorities

| Source | Organization type | Orientation | Language / English | Official status | Ingestion | RSS / feed page | YouTube | Priority / Phase | Topics | Value / access notes |
|---|---|---|---|---|---|---|---|---|---|---|
| [National People's Congress (全国人大)](http://www.npc.gov.cn/) | Legislature | Official | Simplified Chinese / EN: Limited | Yes - official PRC government/institution | changedetection.io | — | — | Critical / Phase 1 | Laws; legislation; sessions; committee decisions | Primary-source PRC government, legal, economic, security, Taiwan-policy, or maritime information. Pages may be updated/removed; preserve versions and retrieval timestamps. Access may vary by region. |
| [Supreme People's Court (最高人民法院)](https://www.court.gov.cn/) | Court | Official | Simplified Chinese / EN: Limited | Yes - official PRC government/institution | changedetection.io | — | — | Critical / Phase 1 | Judicial interpretations; major cases; court policy | Primary-source PRC government, legal, economic, security, Taiwan-policy, or maritime information. Pages may be updated/removed; preserve versions and retrieval timestamps. Access may vary by region. |
| [Supreme People's Procuratorate (最高人民检察院)](https://www.spp.gov.cn/) | Prosecutorial authority | Official | Simplified Chinese / EN: Limited | Yes - official PRC government/institution | changedetection.io | — | — | High / Phase 1 | Prosecutions; anti-corruption; major cases | Primary-source PRC government, legal, economic, security, Taiwan-policy, or maritime information. Pages may be updated/removed; preserve versions and retrieval timestamps. Access may vary by region. |

## Government, Executive, Defense, Security & Law Enforcement

| Source | Organization type | Orientation | Language / English | Official status | Ingestion | RSS / feed page | YouTube | Priority / Phase | Topics | Value / access notes |
|---|---|---|---|---|---|---|---|---|---|---|
| [China Coast Guard (中国海警局)](https://www.ccg.gov.cn/) | Coast guard / law enforcement | Official | Simplified Chinese / EN: Limited | Yes - official PRC government/institution | changedetection.io | — | — | Critical / Phase 1 | Maritime enforcement; East/South China Sea; patrols | Primary-source PRC government, legal, economic, security, Taiwan-policy, or maritime information. Pages may be updated/removed; preserve versions and retrieval timestamps. Access may vary by region. |
| [Ministry of Foreign Affairs (外交部)](https://www.mfa.gov.cn/) | Foreign ministry | Official | Simplified Chinese / EN: Yes | Yes - official PRC government/institution | changedetection.io | — | — | Critical / Phase 1 | Diplomacy; spokesperson briefings; sanctions; Taiwan | Primary-source PRC government, legal, economic, security, Taiwan-policy, or maritime information. Pages may be updated/removed; preserve versions and retrieval timestamps. Access may vary by region. |
| [Ministry of National Defense (国防部)](http://www.mod.gov.cn/) | Defense ministry | Official | Simplified Chinese / EN: Limited | Yes - official PRC government/institution | changedetection.io | — | — | Critical / Phase 1 | PLA; defense policy; press briefings; exercises | Primary-source PRC government, legal, economic, security, Taiwan-policy, or maritime information. Pages may be updated/removed; preserve versions and retrieval timestamps. Access may vary by region. |
| [State Council of the PRC (中国政府网)](https://www.gov.cn/) | Executive government portal | Official | Simplified Chinese / EN: Yes | Yes - official PRC government/institution | changedetection.io | — | — | Critical / Phase 1 | State Council; regulations; policy; leadership | Primary-source PRC government, legal, economic, security, Taiwan-policy, or maritime information. Pages may be updated/removed; preserve versions and retrieval timestamps. Access may vary by region. |
| [Taiwan Affairs Office of the State Council (国台办)](https://www.gwytb.gov.cn/) | Government agency | Official | Simplified Chinese / EN: Limited | Yes - official PRC government/institution | changedetection.io | — | — | Critical / Phase 1 | Taiwan; cross-strait; press conferences; policy | Primary-source PRC government, legal, economic, security, Taiwan-policy, or maritime information. Pages may be updated/removed; preserve versions and retrieval timestamps. Access may vary by region. |
| [Ministry of Commerce (商务部)](http://www.mofcom.gov.cn/) | Government ministry | Official | Simplified Chinese / EN: Limited | Yes - official PRC government/institution | changedetection.io | — | — | High / Phase 2 | Trade; export controls; sanctions; foreign investment | Primary-source PRC government, legal, economic, security, Taiwan-policy, or maritime information. Pages may be updated/removed; preserve versions and retrieval timestamps. Access may vary by region. |
| [Ministry of Public Security (公安部)](https://www.mps.gov.cn/) | Police ministry | Official | Simplified Chinese / EN: Limited | Yes - official PRC government/institution | changedetection.io | — | — | High / Phase 2 | Police; crime; border/security; campaigns | Primary-source PRC government, legal, economic, security, Taiwan-policy, or maritime information. Pages may be updated/removed; preserve versions and retrieval timestamps. Access may vary by region. |
| [People's Bank of China (中国人民银行)](http://www.pbc.gov.cn/) | Central bank | Official | Simplified Chinese / EN: Limited | Yes - official PRC government/institution | changedetection.io | — | — | High / Phase 2 | Monetary policy; financial regulation; data | Primary-source PRC government, legal, economic, security, Taiwan-policy, or maritime information. Pages may be updated/removed; preserve versions and retrieval timestamps. Access may vary by region. |

## Think Tanks, Research Institutes & Universities

| Source | Organization type | Orientation | Language / English | Official status | Ingestion | RSS / feed page | YouTube | Priority / Phase | Topics | Value / access notes |
|---|---|---|---|---|---|---|---|---|---|---|
| [China Media Project](https://chinamediaproject.org/) | Independent research/news | Independent / critical media research | English/Chinese / EN: Yes | No | Native RSS | https://chinamediaproject.org/feed/ | — | Critical / Phase 1 | Propaganda; media language; CCP discourse | High-value Chinese state, commercial, business, technology, cyber, or independent monitoring source. Analysis-focused. |
| [China Institute of International Studies (CIIS)](https://www.ciis.org.cn/) | Foreign-policy think tank | Foreign Ministry-affiliated | Simplified Chinese / EN: Yes | Government/state-affiliated research | changedetection.io | — | — | High / Phase 2 | Foreign policy; U.S.-China; Taiwan; security; economy | High-value monitoring source for the platform. Low-volume, report/event-heavy; some sites have inconsistent accessibility. |
| [China Institutes of Contemporary International Relations (CICIR)](http://www.cicir.ac.cn/) | Think tank | State-affiliated / security research | Simplified Chinese / EN: Yes | Government/state-affiliated research | changedetection.io | — | — | High / Phase 2 | Foreign policy; U.S.-China; Taiwan; security; economy | High-value monitoring source for the platform. Low-volume, report/event-heavy; some sites have inconsistent accessibility. |
| [GreatFire.org](https://en.greatfire.org/) | Digital-rights monitoring organization | Independent / digital rights | English/Chinese / EN: Yes | No | Direct scraping | — | — | High / Phase 2 | Censorship; Great Firewall; blocked sites | High-value Chinese state, commercial, business, technology, cyber, or independent monitoring source. Technical data may need custom parser. |
| [Peking University Institute of International and Strategic Studies](https://en.iiss.pku.edu.cn/) | University policy center | Academic / policy | Simplified Chinese / EN: Yes | No | changedetection.io | — | — | High / Phase 2 | Foreign policy; U.S.-China; Taiwan; security; economy | High-value monitoring source for the platform. Low-volume, report/event-heavy; some sites have inconsistent accessibility. |
| [Shanghai Institutes for International Studies (SIIS)](https://www.siis.org.cn/) | Think tank | State-affiliated policy institute | Simplified Chinese / EN: Yes | Government/state-affiliated research | Direct scraping | — | — | High / Phase 2 | Foreign policy; U.S.-China; Taiwan; security; economy | High-value monitoring source for the platform. Low-volume, report/event-heavy; some sites have inconsistent accessibility. |
| [Tsinghua Center for International Security and Strategy](https://ciss.tsinghua.edu.cn/) | University policy center | Academic / policy | Simplified Chinese / EN: Yes | No | changedetection.io | — | — | High / Phase 2 | Foreign policy; U.S.-China; Taiwan; security; economy | High-value monitoring source for the platform. Low-volume, report/event-heavy; some sites have inconsistent accessibility. |
| [Center for China and Globalization (CCG)](http://en.ccg.org.cn/) | Think tank | Non-governmental / establishment-linked | Simplified Chinese / EN: Yes | No | Direct scraping | — | — | Medium / Phase 2 | Foreign policy; U.S.-China; Taiwan; security; economy | High-value monitoring source for the platform. Low-volume, report/event-heavy; some sites have inconsistent accessibility. |
| [Chinese Academy of Social Sciences (CASS)](http://www.cass.cn/) | National research academy | State research institution | Simplified Chinese / EN: Yes | Government/state-affiliated research | changedetection.io | — | — | Medium / Phase 2 | Foreign policy; U.S.-China; Taiwan; security; economy | High-value monitoring source for the platform. Low-volume, report/event-heavy; some sites have inconsistent accessibility. |
| [Fudan University Institute of International Studies](https://iis.fudan.edu.cn/) | University policy center | Academic / policy | Simplified Chinese / EN: Yes | No | changedetection.io | — | — | Medium / Phase 2 | Foreign policy; U.S.-China; Taiwan; security; economy | High-value monitoring source for the platform. Low-volume, report/event-heavy; some sites have inconsistent accessibility. |

# North Korea / DPRK Monitoring

## Major National / Political News

| Source | Organization type | Orientation | Language / English | Official status | Ingestion | RSS / feed page | YouTube | Priority / Phase | Topics | Value / access notes |
|---|---|---|---|---|---|---|---|---|---|---|
| [Korean Central News Agency (KCNA)](http://www.kcna.kp/) | State news agency | DPRK state media | Korean / EN: Yes | Yes - official DPRK source | Direct scraping | — | — | Critical / Phase 1 | Leadership; military; diplomacy; state policy | High-value official, specialist, sanctions, nuclear, human-rights, or external DPRK monitoring source. Intermittent accessibility, DNS/TLS/geoblocking; retries/snapshots needed. |

## Independent & Investigative Media

| Source | Organization type | Orientation | Language / English | Official status | Ingestion | RSS / feed page | YouTube | Priority / Phase | Topics | Value / access notes |
|---|---|---|---|---|---|---|---|---|---|---|
| [Daily NK](https://www.dailynk.com/) | Specialist North Korea publication | Independent / anti-regime reporting | English/Multilingual / EN: Yes | No | Native RSS | https://www.dailynk.com/english/feed/ | — | Critical / Phase 1 | Inside DPRK; markets; border; human rights | High-value official, specialist, sanctions, nuclear, human-rights, or external DPRK monitoring source. Source verification can be difficult by nature; track corroboration. |
| [NK News](https://www.nknews.org/) | Specialist North Korea publication | Independent / specialist | English/Multilingual / EN: Yes | No | Direct scraping | — | — | Critical / Phase 1 | DPRK politics; economy; diplomacy; daily developments | High-value official, specialist, sanctions, nuclear, human-rights, or external DPRK monitoring source. Strong paywall; subscription/session handling required. |

## Technology & Cybersecurity

| Source | Organization type | Orientation | Language / English | Official status | Ingestion | RSS / feed page | YouTube | Priority / Phase | Topics | Value / access notes |
|---|---|---|---|---|---|---|---|---|---|---|
| [North Korea Tech](https://www.northkoreatech.org/) | Specialist technology publication | Independent / specialist | English/Multilingual / EN: Yes | No | Native RSS | https://www.northkoreatech.org/feed/ | — | High / Phase 1 | DPRK internet; media; telecom; cyber | High-value official, specialist, sanctions, nuclear, human-rights, or external DPRK monitoring source. Low-volume specialist source. |

## Government, Executive, Defense, Security & Law Enforcement

| Source | Organization type | Orientation | Language / English | Official status | Ingestion | RSS / feed page | YouTube | Priority / Phase | Topics | Value / access notes |
|---|---|---|---|---|---|---|---|---|---|---|
| [DPRK Ministry of Foreign Affairs](http://www.mfa.gov.kp/) | Foreign ministry | Official | English/Multilingual / EN: Yes | Yes - official DPRK source | changedetection.io | — | — | Critical / Phase 1 | Diplomacy; statements; U.S.; sanctions | High-value official, specialist, sanctions, nuclear, human-rights, or external DPRK monitoring source. Intermittent access; low-volume high-value. |

## Think Tanks, Research Institutes & Universities

| Source | Organization type | Orientation | Language / English | Official status | Ingestion | RSS / feed page | YouTube | Priority / Phase | Topics | Value / access notes |
|---|---|---|---|---|---|---|---|---|---|---|
| [38 North](https://www.38north.org/) | Specialist North Korea publication | Independent / specialist | English/Multilingual / EN: Yes | No | Native RSS | https://www.38north.org/feed/ | — | Critical / Phase 1 | Nuclear; missiles; satellite imagery; economy; policy | High-value official, specialist, sanctions, nuclear, human-rights, or external DPRK monitoring source. Analysis-focused; preserve imagery/technical annexes. |
| [CSIS Beyond Parallel](https://beyondparallel.csis.org/) | Think tank project | Bipartisan / specialist | English/Multilingual / EN: Yes | No | Direct scraping | — | — | Critical / Phase 1 | Missiles; bases; satellite imagery; leadership | High-value official, specialist, sanctions, nuclear, human-rights, or external DPRK monitoring source. Image-heavy; archive imagery metadata. |
| [Committee for Human Rights in North Korea (HRNK)](https://www.hrnk.org/) | Nonprofit research organization | Independent / human-rights advocacy | English/Multilingual / EN: Yes | No | Direct scraping | — | — | High / Phase 2 | Human rights; prison camps; satellite imagery | High-value official, specialist, sanctions, nuclear, human-rights, or external DPRK monitoring source. Reports/PDFs; advocacy perspective. |
| [KINU DPRK Research](https://www.kinu.or.kr/) | Research institute | Government-funded South Korean research | English/Multilingual / EN: Yes | No | Direct scraping | — | — | High / Phase 2 | DPRK politics; human rights; unification | High-value official, specialist, sanctions, nuclear, human-rights, or external DPRK monitoring source. PDF-heavy. |

## International Organizations & Diplomatic Sources

| Source | Organization type | Orientation | Language / English | Official status | Ingestion | RSS / feed page | YouTube | Priority / Phase | Topics | Value / access notes |
|---|---|---|---|---|---|---|---|---|---|---|
| [International Atomic Energy Agency (IAEA) - DPRK](https://www.iaea.org/topics/dprk) | International organization | Official international organization | English/Multilingual / EN: Yes | Yes - official international/South Korean institution | changedetection.io | — | — | Critical / Phase 1 | Nuclear program; safeguards; satellite observations | High-value official, specialist, sanctions, nuclear, human-rights, or external DPRK monitoring source. Low volume; high-value reports/PDFs. |
| [UN Security Council DPRK Sanctions Committee (1718)](https://main.un.org/securitycouncil/en/sanctions/1718) | International organization | Official UN | English/Multilingual / EN: Yes | Yes - official international/South Korean institution | changedetection.io | — | — | Critical / Phase 1 | Sanctions; designated entities; implementation notices | High-value official, specialist, sanctions, nuclear, human-rights, or external DPRK monitoring source. Monitor current committee and related mechanisms. |
| [Multilateral Sanctions Monitoring Team (MSMT)](https://www.state.gov/) | International monitoring mechanism | Multilateral government mechanism | English/Multilingual / EN: Yes | No | changedetection.io | — | — | High / Phase 2 | DPRK sanctions evasion; monitoring reports | High-value official, specialist, sanctions, nuclear, human-rights, or external DPRK monitoring source. Reports may be hosted across participating governments; no single canonical feed. |
| [UN Human Rights Office - DPRK](https://seoul.ohchr.org/en) | International organization | Official UN | English/Multilingual / EN: Yes | Yes - official international/South Korean institution | changedetection.io | — | — | High / Phase 1 | DPRK human rights; investigations; reports | High-value official, specialist, sanctions, nuclear, human-rights, or external DPRK monitoring source. Report-heavy; monitor Seoul office and OHCHR releases. |

## YouTube & Video Sources

| Source | Organization type | Orientation | Language / English | Official status | Ingestion | RSS / feed page | YouTube | Priority / Phase | Topics | Value / access notes |
|---|---|---|---|---|---|---|---|---|---|---|
| [Radio Free Asia Korean](https://www.rfa.org/korean/) | International broadcaster | U.S.-funded international broadcaster | English/Multilingual / EN: Yes | No | YouTube/yt-dlp | — | https://www.youtube.com/@RFAVideo | High / Phase 2 | North Korea; human rights; defectors; China border | High-value official, specialist, sanctions, nuclear, human-rights, or external DPRK monitoring source. Blocked in some target environments; use web plus video/audio. |
| [VOA Korean](https://www.voakorea.com/) | International broadcaster | U.S.-funded international broadcaster | English/Multilingual / EN: Yes | No | YouTube/yt-dlp | — | https://www.youtube.com/@voakorea | High / Phase 2 | North Korea; U.S. policy; sanctions; diplomacy | High-value official, specialist, sanctions, nuclear, human-rights, or external DPRK monitoring source. Web/video feeds vary. |

## Other High-Value Sources

| Source | Organization type | Orientation | Language / English | Official status | Ingestion | RSS / feed page | YouTube | Priority / Phase | Topics | Value / access notes |
|---|---|---|---|---|---|---|---|---|---|---|
| [North Korea Information Portal (Unification Ministry)](https://nkinfo.unikorea.go.kr/) | South Korean government monitoring | Official South Korean government | English/Multilingual / EN: Yes | Yes - official international/South Korean institution | changedetection.io | — | — | Critical / Phase 1 | DPRK data; leadership; institutions; statistics | High-value official, specialist, sanctions, nuclear, human-rights, or external DPRK monitoring source. Dynamic database pages; stable identifiers needed. |
| [Rodong Sinmun (로동신문)](http://www.rodong.rep.kp/) | Party newspaper | Workers' Party official media | Korean / EN: Yes | Yes - official DPRK source | Direct scraping | — | — | Critical / Phase 1 | Leadership; ideology; domestic policy; military | High-value official, specialist, sanctions, nuclear, human-rights, or external DPRK monitoring source. Intermittent .kp accessibility; archive every version. |
| [Korea Risk Group](https://www.korearisk.com/) | Commercial intelligence organization | Independent / commercial intelligence | English/Multilingual / EN: Yes | No | Direct scraping | — | — | High / Phase 2 | DPRK risk; markets; sanctions; geopolitical intelligence | High-value official, specialist, sanctions, nuclear, human-rights, or external DPRK monitoring source. Subscription/commercial access. |
| [NK Leadership Watch](https://www.nkleadershipwatch.org/) | Specialist research blog | Independent / specialist | English/Multilingual / EN: Yes | No | Native RSS | https://www.nkleadershipwatch.org/feed/ | — | High / Phase 1 | Leadership; elite politics; personnel | High-value official, specialist, sanctions, nuclear, human-rights, or external DPRK monitoring source. Publishing cadence can be irregular. |
| [NK Pro](https://www.nknews.org/pro/) | Specialist intelligence service | Independent / commercial intelligence | English/Multilingual / EN: Yes | No | Direct scraping | — | — | High / Phase 2 | Leadership; trade; maritime; sanctions; data | High-value official, specialist, sanctions, nuclear, human-rights, or external DPRK monitoring source. Hard paywall/subscription and licensing constraints. |
| [Naenara](http://www.naenara.com.kp/) | Official DPRK web portal | DPRK state portal | English/Multilingual / EN: Yes | Yes - official DPRK source | Direct scraping | — | — | High / Phase 1 | Official publications; culture; policy; institutions | High-value official, specialist, sanctions, nuclear, human-rights, or external DPRK monitoring source. Connectivity can be unstable; legacy HTML. |
| [Voice of Korea](http://www.vok.rep.kp/) | State international broadcaster | DPRK state broadcaster | English/Multilingual / EN: Yes | Yes - official DPRK source | Direct scraping | — | — | High / Phase 1 | Foreign-facing propaganda; leadership; culture | High-value official, specialist, sanctions, nuclear, human-rights, or external DPRK monitoring source. Audio/media extraction and intermittent access. |

# Philippines

## Major National / Political News

| Source | Organization type | Orientation | Language / English | Official status | Ingestion | RSS / feed page | YouTube | Priority / Phase | Topics | Value / access notes |
|---|---|---|---|---|---|---|---|---|---|---|
| [ABS-CBN News](https://www.abs-cbn.com/news) | Broadcast/digital news | Mainstream | English/Filipino / EN: Yes | No | Native RSS | https://www.abs-cbn.com/rss.aspx/news | https://www.youtube.com/@ABSCBNNews | Critical / Phase 1 | Politics; breaking news; regions; business | High-value Philippine national, regional, investigative, business, technology, or political source. RSS endpoint needs health-check after platform/site changes. |
| [GMA News Online](https://www.gmanetwork.com/news/) | Broadcast/digital news | Mainstream | English/Filipino / EN: Yes | No | Native RSS | https://www.gmanetwork.com/news/rss/ | https://www.youtube.com/@gmanews | Critical / Phase 1 | Politics; regions; business; world; investigations | High-value Philippine national, regional, investigative, business, technology, or political source. Harvest exact category feed endpoints from RSS page. |
| [Philippine Daily Inquirer / Inquirer.net](https://www.inquirer.net/) | Newspaper/digital | Mainstream | English/Filipino / EN: Yes | No | Native RSS | https://newsinfo.inquirer.net/feed | — | Critical / Phase 1 | Politics; national; regions; business; opinion | High-value Philippine national, regional, investigative, business, technology, or political source. Section feeds may live on subdomains. |
| [Manila Bulletin](https://mb.com.ph/) | Newspaper/digital | Mainstream / traditional | English/Filipino / EN: Yes | No | Direct scraping | — | — | High / Phase 2 | Politics; national; business; regions | High-value Philippine national, regional, investigative, business, technology, or political source. No broad RSS verified. |
| [News5 / One News](https://news.tv5.com.ph/) | Broadcast/digital news | Mainstream | English/Filipino / EN: Yes | No | YouTube/yt-dlp | — | https://www.youtube.com/@News5Everywhere | High / Phase 2 | Politics; breaking; business; live news | High-value Philippine national, regional, investigative, business, technology, or political source. Video-heavy; site/feed status can change. |
| [The Philippine Star / Philstar.com](https://www.philstar.com/) | Newspaper/digital | Mainstream | English/Filipino / EN: Yes | No | Direct scraping | — | — | High / Phase 2 | Politics; national; business; regions; opinion | High-value Philippine national, regional, investigative, business, technology, or political source. No broad RSS verified. |
| [Daily Tribune](https://tribune.net.ph/) | Newspaper/digital | Mainstream / varied | English/Filipino / EN: Yes | No | Direct scraping | — | — | Medium / Phase 2 | Politics; national; business; opinion | High-value Philippine national, regional, investigative, business, technology, or political source. No broad RSS verified. |

## Regional & Local News

| Source | Organization type | Orientation | Language / English | Official status | Ingestion | RSS / feed page | YouTube | Priority / Phase | Topics | Value / access notes |
|---|---|---|---|---|---|---|---|---|---|---|
| [SunStar](https://www.sunstar.com.ph/) | Regional news network | Regional mainstream | English/Filipino / EN: Yes | No | Direct scraping | — | — | High / Phase 2 | Cebu; Davao; regions; local politics | High-value Philippine national, regional, investigative, business, technology, or political source. Multiple city editions; no broad RSS verified. |
| [Cebu Daily News](https://cebudailynews.inquirer.net/) | Regional newspaper | Regional mainstream | English/Filipino / EN: Yes | No | Native RSS | https://cebudailynews.inquirer.net/feed | — | Medium / Phase 2 | Cebu; Visayas; local government | High-value Philippine national, regional, investigative, business, technology, or political source. Inquirer network feed structure. |
| [Mindanao Times](https://mindanaotimes.com.ph/) | Regional newspaper | Regional mainstream | English/Filipino / EN: Yes | No | Native RSS | https://mindanaotimes.com.ph/feed/ | — | Medium / Phase 2 | Davao; Mindanao; local affairs | High-value Philippine national, regional, investigative, business, technology, or political source. WordPress feed. |

## Independent & Investigative Media

| Source | Organization type | Orientation | Language / English | Official status | Ingestion | RSS / feed page | YouTube | Priority / Phase | Topics | Value / access notes |
|---|---|---|---|---|---|---|---|---|---|---|
| [Philippine Center for Investigative Journalism (PCIJ)](https://pcij.org/) | Nonprofit investigative newsroom | Independent / nonprofit | English/Filipino / EN: Yes | No | Native RSS | https://pcij.org/feed/ | — | Critical / Phase 1 | Corruption; governance; elections; data journalism | High-value Philippine national, regional, investigative, business, technology, or political source. Low-volume/high-value; archive datasets/documents. |
| [Rappler](https://www.rappler.com/) | Digital news organization | Independent / liberal-leaning perceived | English/Filipino / EN: Yes | No | Native RSS | https://www.rappler.com/feed/ | https://www.youtube.com/@Rappler | Critical / Phase 1 | Politics; elections; disinformation; investigations | High-value Philippine national, regional, investigative, business, technology, or political source. Robots/anti-bot may affect crawlers; feed health-check. |
| [VERA Files](https://verafiles.org/) | Nonprofit investigative newsroom | Independent / nonprofit | English/Filipino / EN: Yes | No | Native RSS | https://verafiles.org/feed/ | — | Critical / Phase 1 | Investigations; elections; fact checks; disinformation | High-value Philippine national, regional, investigative, business, technology, or political source. Low-medium volume. |
| [MindaNews](https://mindanews.com/) | Regional nonprofit news | Independent / regional | English/Filipino / EN: Yes | No | Native RSS | https://mindanews.com/feed/ | — | High / Phase 2 | Mindanao; BARMM; conflict; local politics | High-value Philippine national, regional, investigative, business, technology, or political source. Important southern Philippines perspective. |

## Political / Ideological & YouTube Media

| Source | Organization type | Orientation | Language / English | Official status | Ingestion | RSS / feed page | YouTube | Priority / Phase | Topics | Value / access notes |
|---|---|---|---|---|---|---|---|---|---|---|
| [The Manila Times](https://www.manilatimes.net/) | Newspaper | Conservative-leaning editorial reputation | English/Filipino / EN: Yes | No | Direct scraping | — | — | High / Phase 2 | Politics; business; opinion; national | High-value Philippine national, regional, investigative, business, technology, or political source. Paywall/subscription on some content. |

## Business & Financial News

| Source | Organization type | Orientation | Language / English | Official status | Ingestion | RSS / feed page | YouTube | Priority / Phase | Topics | Value / access notes |
|---|---|---|---|---|---|---|---|---|---|---|
| [BusinessWorld](https://www.bworldonline.com/) | Business newspaper | Business-focused | English/Filipino / EN: Yes | No | Native RSS | https://www.bworldonline.com/feed/ | — | Critical / Phase 1 | Economy; companies; markets; policy | High-value Philippine national, regional, investigative, business, technology, or political source. Some premium content. |
| [BusinessMirror](https://businessmirror.com.ph/) | Business newspaper | Business-focused | English/Filipino / EN: Yes | No | Native RSS | https://businessmirror.com.ph/feed/ | — | High / Phase 2 | Economy; trade; companies; policy | High-value Philippine national, regional, investigative, business, technology, or political source. WordPress feed. |
| [Bilyonaryo](https://bilyonaryo.com/) | Business/digital publication | Business/elite-focused | English/Filipino / EN: Yes | No | Native RSS | https://bilyonaryo.com/feed/ | — | Medium / Phase 2 | Corporate elites; finance; politics-business links | High-value Philippine national, regional, investigative, business, technology, or political source. Tabloid-style tone at times; verify claims. |

## Technology & Cybersecurity

| Source | Organization type | Orientation | Language / English | Official status | Ingestion | RSS / feed page | YouTube | Priority / Phase | Topics | Value / access notes |
|---|---|---|---|---|---|---|---|---|---|---|
| [Newsbytes.PH](https://newsbytes.ph/) | Technology publication | Technology specialist | English/Filipino / EN: Yes | No | Native RSS | https://newsbytes.ph/feed/ | — | High / Phase 2 | Technology; cyber; telecom; digital policy | High-value Philippine national, regional, investigative, business, technology, or political source. WordPress feed. |

## Legislatures, Courts & Election Authorities

| Source | Organization type | Orientation | Language / English | Official status | Ingestion | RSS / feed page | YouTube | Priority / Phase | Topics | Value / access notes |
|---|---|---|---|---|---|---|---|---|---|---|
| [Commission on Elections (COMELEC)](https://comelec.gov.ph/) | Election commission | Official | English/Filipino / EN: Yes | Yes - official Philippine government/institution | Playwright | — | — | Critical / Phase 2 | Elections; resolutions; results; voter rules | Primary-source Philippine executive, legislative, judicial, election, defense, foreign-policy, maritime, or security information. Automated access can be unreliable. |
| [House of Representatives of the Philippines](https://www.congress.gov.ph/) | Legislature | Official | English/Filipino / EN: Yes | Yes - official Philippine government/institution | changedetection.io | — | — | Critical / Phase 1 | Bills; committees; press releases; hearings | Primary-source Philippine executive, legislative, judicial, election, defense, foreign-policy, maritime, or security information. Multiple pages/document types. |
| [Senate of the Philippines](https://legacy.senate.gov.ph/) | Legislature | Official | English/Filipino / EN: Yes | Yes - official Philippine government/institution | Playwright | — | — | Critical / Phase 2 | Bills; hearings; senators; press releases | Primary-source Philippine executive, legislative, judicial, election, defense, foreign-policy, maritime, or security information. Legacy site/automated access restrictions. |
| [Supreme Court of the Philippines](https://sc.judiciary.gov.ph/) | Court | Official | English/Filipino / EN: Yes | Yes - official Philippine government/institution | changedetection.io | — | https://www.youtube.com/@SupremeCourtPH | Critical / Phase 1 | Decisions; resolutions; current cases; announcements | Primary-source Philippine executive, legislative, judicial, election, defense, foreign-policy, maritime, or security information. PDF-heavy. |

## Government, Executive, Defense, Security & Law Enforcement

| Source | Organization type | Orientation | Language / English | Official status | Ingestion | RSS / feed page | YouTube | Priority / Phase | Topics | Value / access notes |
|---|---|---|---|---|---|---|---|---|---|---|
| [Armed Forces of the Philippines (AFP)](https://www.afp.mil.ph/) | Military | Official | English/Filipino / EN: Yes | Yes - official Philippine government/institution | changedetection.io | — | — | Critical / Phase 1 | Military operations; West Philippine Sea; exercises | Primary-source Philippine executive, legislative, judicial, election, defense, foreign-policy, maritime, or security information. Active news pages; no broad RSS. |
| [Department of Foreign Affairs (DFA)](https://dfa.gov.ph/) | Foreign ministry | Official | English/Filipino / EN: Yes | Yes - official Philippine government/institution | changedetection.io | — | — | Critical / Phase 1 | Diplomacy; China; treaties; consular; statements | Primary-source Philippine executive, legislative, judicial, election, defense, foreign-policy, maritime, or security information. Automated access may be inconsistent. |
| [Department of National Defense (DND)](https://www.dnd.gov.ph/) | Defense ministry | Official | English/Filipino / EN: Yes | Yes - official Philippine government/institution | changedetection.io | — | — | Critical / Phase 1 | Defense policy; acquisitions; security | Primary-source Philippine executive, legislative, judicial, election, defense, foreign-policy, maritime, or security information. Access can be inconsistent. |
| [National Security Council of the Philippines](https://nsc.gov.ph/) | National security council | Official | English/Filipino / EN: Yes | Yes - official Philippine government/institution | changedetection.io | — | — | Critical / Phase 1 | National security; WPS; insurgency; policy | Primary-source Philippine executive, legislative, judicial, election, defense, foreign-policy, maritime, or security information. Low-volume high-value. |
| [Office of the President of the Philippines](https://president.gov.ph/) | Executive office | Official | English/Filipino / EN: Yes | Yes - official Philippine government/institution | Playwright | — | — | Critical / Phase 1 | Presidential statements; appointments; policy | Primary-source Philippine executive, legislative, judicial, election, defense, foreign-policy, maritime, or security information. Automated access may return 403/WAF. |
| [Official Gazette of the Republic of the Philippines](https://www.officialgazette.gov.ph/) | Official publication | Official | English/Filipino / EN: Yes | Yes - official Philippine government/institution | Playwright | — | — | Critical / Phase 1 | Executive orders; proclamations; laws; official documents | Primary-source Philippine executive, legislative, judicial, election, defense, foreign-policy, maritime, or security information. Automated access can be blocked/403. |
| [Philippine Coast Guard](https://coastguard.gov.ph/) | Coast guard | Official | English/Filipino / EN: Yes | Yes - official Philippine government/institution | changedetection.io | — | — | Critical / Phase 1 | West Philippine Sea; maritime incidents; rescues | Primary-source Philippine executive, legislative, judicial, election, defense, foreign-policy, maritime, or security information. Press/social may be faster than site. |
| [Philippine Navy](https://www.navy.mil.ph/) | Military branch | Official | English/Filipino / EN: Yes | Yes - official Philippine government/institution | changedetection.io | — | — | Critical / Phase 1 | Naval operations; WPS; exercises | Primary-source Philippine executive, legislative, judicial, election, defense, foreign-policy, maritime, or security information. Monitor news/releases. |
| [Philippine News Agency (PNA)](https://www.pna.gov.ph/) | Government news agency | Official government newswire | English/Filipino / EN: Yes | Yes - government newswire | Direct scraping | — | — | Critical / Phase 1 | Politics; government; economy; regions; foreign affairs | High-value Philippine national, regional, investigative, business, technology, or political source. Government perspective; no broad RSS verified. |
| [Presidential Communications Office (PCO)](https://pco.gov.ph/) | Executive communications office | Official | English/Filipino / EN: Yes | Yes - official Philippine government/institution | changedetection.io | — | https://www.youtube.com/@PresidentialCommunicationsOffice | Critical / Phase 1 | Palace briefings; speeches; press releases | Primary-source Philippine executive, legislative, judicial, election, defense, foreign-policy, maritime, or security information. Some routes may block automated clients. |
| [Philippine Air Force](https://www.paf.mil.ph/) | Military branch | Official | English/Filipino / EN: Yes | Yes - official Philippine government/institution | changedetection.io | — | — | High / Phase 2 | Air operations; exercises; procurement | Primary-source Philippine executive, legislative, judicial, election, defense, foreign-policy, maritime, or security information. No broad RSS. |
| [Philippine Army](https://army.mil.ph/) | Military branch | Official | English/Filipino / EN: Yes | Yes - official Philippine government/institution | changedetection.io | — | — | High / Phase 2 | Army operations; insurgency; exercises | Primary-source Philippine executive, legislative, judicial, election, defense, foreign-policy, maritime, or security information. No broad RSS. |
| [Philippine National Police (PNP)](https://pnp.gov.ph/) | Police agency | Official | English/Filipino / EN: Yes | Yes - official Philippine government/institution | changedetection.io | — | — | High / Phase 2 | Crime; investigations; public safety | Primary-source Philippine executive, legislative, judicial, election, defense, foreign-policy, maritime, or security information. Regional police offices may need separate monitors. |
| [National Intelligence Coordinating Agency (NICA)](https://nica.gov.ph/) | Intelligence agency | Official | English/Filipino / EN: Yes | Yes - official Philippine government/institution | changedetection.io | — | — | Medium / Phase 2 | Public intelligence notices; national security | Primary-source Philippine executive, legislative, judicial, election, defense, foreign-policy, maritime, or security information. Very sparse output. |

## Think Tanks, Research Institutes & Universities

| Source | Organization type | Orientation | Language / English | Official status | Ingestion | RSS / feed page | YouTube | Priority / Phase | Topics | Value / access notes |
|---|---|---|---|---|---|---|---|---|---|---|
| [Stratbase ADR Institute](https://adrinstitute.org/) | Think tank | Policy institute | English / EN: Yes | No | Direct scraping | — | — | High / Phase 2 | Foreign policy; China; defense; governance | High-value monitoring source for the platform. Low-frequency research/event pages; verify publication URLs during onboarding. |
| [UP Institute for Maritime Affairs and Law of the Sea](https://law.upd.edu.ph/) | University/policy center | Academic | English / EN: Yes | No | changedetection.io | — | — | High / Phase 2 | South China Sea; maritime law; UNCLOS | High-value monitoring source for the platform. Low-frequency research/event pages; verify publication URLs during onboarding. |
| [Ateneo Policy Center](https://ateneopolicycenter.com/) | University/policy center | Academic | English / EN: Yes | No | changedetection.io | — | — | Medium / Phase 2 | Governance; democracy; public policy | High-value monitoring source for the platform. Low-frequency research/event pages; verify publication URLs during onboarding. |

## YouTube & Video Sources

| Source | Organization type | Orientation | Language / English | Official status | Ingestion | RSS / feed page | YouTube | Priority / Phase | Topics | Value / access notes |
|---|---|---|---|---|---|---|---|---|---|---|
| [Radio Television Malacañang (RTVM)](https://rtvm.gov.ph/) | Official government broadcaster | Official | English/Filipino / EN: Yes | Yes - official Philippine government/institution | YouTube/yt-dlp | — | https://www.youtube.com/@RTVMalacanang | Critical / Phase 1 | Presidential events; ceremonies; briefings | Primary-source Philippine executive, legislative, judicial, election, defense, foreign-policy, maritime, or security information. Captions inconsistent; ASR fallback useful. |

# Indo-Pacific / Regional

## Independent & Investigative Media

| Source | Organization type | Orientation | Language / English | Official status | Ingestion | RSS / feed page | YouTube | Priority / Phase | Topics | Value / access notes |
|---|---|---|---|---|---|---|---|---|---|---|
| [BenarNews](https://www.benarnews.org/) | International regional news service | U.S.-funded regional service | English / EN: Yes | No | Direct scraping | — | — | High / Phase 1 | Southeast Asia; security; human rights; China influence | High-value Indo-Pacific regional media, defense, think-tank, international-organization, or diplomatic source. Blocked in some countries; feed structures vary. |

## Defense, Military, Intelligence & Geopolitics

| Source | Organization type | Orientation | Language / English | Official status | Ingestion | RSS / feed page | YouTube | Priority / Phase | Topics | Value / access notes |
|---|---|---|---|---|---|---|---|---|---|---|
| [Janes](https://www.janes.com/) | Defense intelligence publisher | Commercial defense intelligence | English / EN: Yes | No | Direct scraping | — | — | Critical / Phase 1 | Military capabilities; order of battle; procurement | High-value Indo-Pacific regional media, defense, think-tank, international-organization, or diplomatic source. Hard paywall/licensing; subscription integration preferable. |
| [Naval News](https://www.navalnews.com/) | Defense trade publication | Specialist / naval | English / EN: Yes | No | Native RSS | https://www.navalnews.com/feed/ | https://www.youtube.com/@NavalNews | Critical / Phase 1 | Navies; shipbuilding; missiles; Indo-Pacific | High-value Indo-Pacific regional media, defense, think-tank, international-organization, or diplomatic source. Some sponsored content. |
| [USNI News](https://news.usni.org/) | Naval publication | Specialist / naval | English / EN: Yes | No | Native RSS | https://news.usni.org/feed/ | — | Critical / Phase 1 | Naval; China; Taiwan; Japan; Philippines | High-value Indo-Pacific regional media, defense, think-tank, international-organization, or diplomatic source. |

## Think Tanks, Research Institutes & Universities

| Source | Organization type | Orientation | Language / English | Official status | Ingestion | RSS / feed page | YouTube | Priority / Phase | Topics | Value / access notes |
|---|---|---|---|---|---|---|---|---|---|---|
| [International Institute for Strategic Studies (IISS)](https://www.iiss.org/) | Think tank | Independent / policy establishment | English / EN: Yes | No | Direct scraping | — | https://www.youtube.com/@IISSorg | Critical / Phase 1 | Military balance; Asia security; strategy | High-value Indo-Pacific regional media, defense, think-tank, international-organization, or diplomatic source. Premium reports/products. |
| [ASPI / The Strategist](https://www.aspistrategist.org.au/) | Think tank | Security-focused policy institute | English / EN: Yes | No | Native RSS | https://www.aspistrategist.org.au/feed/ | — | High / Phase 1 | China; cyber; defense; Indo-Pacific | High-value Indo-Pacific regional media, defense, think-tank, international-organization, or diplomatic source. Analysis/opinion. |
| [Australian National University - East Asia Forum](https://eastasiaforum.org/) | University/policy publication | Academic / policy | English / EN: Yes | No | Native RSS | https://eastasiaforum.org/feed/ | — | High / Phase 2 | East Asia economics; politics; regional affairs | High-value Indo-Pacific regional media, defense, think-tank, international-organization, or diplomatic source. Analysis-focused. |
| [ISEAS – Yusof Ishak Institute](https://www.iseas.edu.sg/) | Research institute | Policy research | English / EN: Yes | No | Direct scraping | — | — | High / Phase 2 | Southeast Asia; China; regional politics | High-value Indo-Pacific regional media, defense, think-tank, international-organization, or diplomatic source. Some publications/paywall. |
| [Lowy Institute / The Interpreter](https://www.lowyinstitute.org/the-interpreter) | Think tank | Center / policy institute | English / EN: Yes | No | Native RSS | https://www.lowyinstitute.org/the-interpreter/rss.xml | — | High / Phase 1 | Indo-Pacific; China; Southeast Asia; diplomacy | High-value Indo-Pacific regional media, defense, think-tank, international-organization, or diplomatic source. Feed health-check. |
| [Pacific Forum](https://pacforum.org/) | Think tank | Policy institute | English / EN: Yes | No | Direct scraping | — | — | High / Phase 2 | Alliances; Indo-Pacific; China; Korea | High-value Indo-Pacific regional media, defense, think-tank, international-organization, or diplomatic source. No broad RSS verified. |
| [RSIS](https://www.rsis.edu.sg/) | University/policy center | Academic / policy | English / EN: Yes | No | Direct scraping | — | — | High / Phase 2 | Security; terrorism; China; Southeast Asia | High-value Indo-Pacific regional media, defense, think-tank, international-organization, or diplomatic source. No broad RSS verified. |
| [Asia Society Policy Institute](https://asiasociety.org/policy-institute) | Think tank | Policy institute | English / EN: Yes | No | Direct scraping | — | — | Medium / Phase 2 | Asia policy; China; diplomacy | High-value Indo-Pacific regional media, defense, think-tank, international-organization, or diplomatic source. No broad RSS verified. |
| [East-West Center](https://www.eastwestcenter.org/) | Research institute | Nonpartisan / research | English / EN: Yes | No | Direct scraping | — | — | Medium / Phase 2 | Asia-Pacific policy; society; media | High-value Indo-Pacific regional media, defense, think-tank, international-organization, or diplomatic source. No broad RSS verified. |

## International Organizations & Diplomatic Sources

| Source | Organization type | Orientation | Language / English | Official status | Ingestion | RSS / feed page | YouTube | Priority / Phase | Topics | Value / access notes |
|---|---|---|---|---|---|---|---|---|---|---|
| [American Institute in Taiwan (AIT)](https://www.ait.org.tw/) | De facto embassy | Official U.S. representative organization | English / EN: Yes | Yes - official international/government institution | changedetection.io | — | — | Critical / Phase 1 | U.S.-Taiwan relations; security; visits | High-value Indo-Pacific regional media, defense, think-tank, international-organization, or diplomatic source. |
| [U.S. Embassy Manila](https://ph.usembassy.gov/) | Embassy | Official | English / EN: Yes | Yes - official international/government institution | changedetection.io | — | — | Critical / Phase 1 | U.S.-Philippines alliance; WPS; exercises | High-value Indo-Pacific regional media, defense, think-tank, international-organization, or diplomatic source. |
| [ASEAN](https://asean.org/) | International organization | Official intergovernmental organization | English / EN: Yes | Yes - official international/government institution | changedetection.io | — | — | High / Phase 1 | Southeast Asia diplomacy; security; summits | High-value Indo-Pacific regional media, defense, think-tank, international-organization, or diplomatic source. Dynamic site. |
| [Asian Development Bank](https://www.adb.org/) | International organization | Official multilateral | English / EN: Yes | Yes - official international/government institution | Native RSS | https://www.adb.org/rss | — | High / Phase 2 | Asia economy; development; infrastructure | High-value Indo-Pacific regional media, defense, think-tank, international-organization, or diplomatic source. Multiple RSS categories; reports/PDFs. |
| [Financial Action Task Force (FATF)](https://www.fatf-gafi.org/) | International organization | Official intergovernmental body | English / EN: Yes | Yes - official international/government institution | changedetection.io | — | — | High / Phase 2 | AML/CFT; sanctions; country evaluations | High-value Indo-Pacific regional media, defense, think-tank, international-organization, or diplomatic source. Report-heavy. |
| [International Atomic Energy Agency (IAEA)](https://www.iaea.org/) | International organization | Official international organization | English / EN: Yes | Yes - official international/government institution | Native RSS | https://www.iaea.org/feeds/topnews | — | High / Phase 1 | Nuclear safeguards; DPRK; nuclear energy; statements | High-value Indo-Pacific regional media, defense, think-tank, international-organization, or diplomatic source. |
| [Taipei Economic and Cultural Representative Office in the U.S. (TECRO)](https://www.roc-taiwan.org/us_en/index.html) | Representative office | Official Taiwan representative office | English / EN: Yes | Yes - official international/government institution | changedetection.io | — | — | High / Phase 2 | Taiwan-U.S. diplomacy; security; statements | High-value Indo-Pacific regional media, defense, think-tank, international-organization, or diplomatic source. |
| [U.S. Embassy Beijing](https://china.usembassy-china.org.cn/) | Embassy | Official | English / EN: Yes | Yes - official international/government institution | changedetection.io | — | — | High / Phase 2 | U.S.-China relations; statements | High-value Indo-Pacific regional media, defense, think-tank, international-organization, or diplomatic source. Blocked inside China in some contexts. |
| [U.S. Embassy Seoul](https://kr.usembassy.gov/) | Embassy | Official | English / EN: Yes | Yes - official international/government institution | changedetection.io | — | — | High / Phase 2 | U.S.-Korea relations; statements | High-value Indo-Pacific regional media, defense, think-tank, international-organization, or diplomatic source. CMS structure changes. |
| [U.S. Embassy Tokyo](https://jp.usembassy.gov/) | Embassy | Official | English / EN: Yes | Yes - official international/government institution | changedetection.io | — | — | High / Phase 2 | U.S.-Japan alliance; diplomacy; security | High-value Indo-Pacific regional media, defense, think-tank, international-organization, or diplomatic source. |
| [UN Security Council](https://main.un.org/securitycouncil/) | International organization | Official UN | English / EN: Yes | Yes - official international/government institution | changedetection.io | — | — | High / Phase 1 | Sanctions; resolutions; DPRK; international security | High-value Indo-Pacific regional media, defense, think-tank, international-organization, or diplomatic source. Monitor press releases and sanctions pages. |
| [APEC](https://www.apec.org/) | International organization | Official intergovernmental forum | English / EN: Yes | Yes - official international/government institution | changedetection.io | — | — | Medium / Phase 2 | Trade; economic policy; leaders' meetings | High-value Indo-Pacific regional media, defense, think-tank, international-organization, or diplomatic source. Low-medium volume. |
| [Asia/Pacific Group on Money Laundering (APG)](https://apgml.org/) | International organization | Official regional body | English / EN: Yes | Yes - official international/government institution | changedetection.io | — | — | Medium / Phase 2 | AML/CFT; mutual evaluations; sanctions implementation | High-value Indo-Pacific regional media, defense, think-tank, international-organization, or diplomatic source. Low frequency. |
| [Embassy of Japan in the United States](https://www.us.emb-japan.go.jp/itprtop_en/index.html) | Embassy | Official | English / EN: Yes | Yes - official international/government institution | changedetection.io | — | — | Medium / Phase 2 | Japan-U.S. diplomacy; security | High-value Indo-Pacific regional media, defense, think-tank, international-organization, or diplomatic source. |
| [Embassy of the Republic of Korea in the U.S.](https://overseas.mofa.go.kr/us-en/index.do) | Embassy | Official | English / EN: Yes | Yes - official international/government institution | changedetection.io | — | — | Medium / Phase 2 | Korea-U.S. diplomacy; policy | High-value Indo-Pacific regional media, defense, think-tank, international-organization, or diplomatic source. |
| [IMF Asia and Pacific](https://www.imf.org/en/Regions/Asia-and-Pacific) | International organization | Official multilateral | English / EN: Yes | Yes - official international/government institution | changedetection.io | — | — | Medium / Phase 2 | Macroeconomy; country surveillance; regional outlook | High-value Indo-Pacific regional media, defense, think-tank, international-organization, or diplomatic source. PDF-heavy. |
| [INTERPOL](https://www.interpol.int/) | International organization | Official international organization | English / EN: Yes | Yes - official international/government institution | Native RSS | https://www.interpol.int/rss | — | Medium / Phase 2 | Transnational crime; cybercrime; notices | High-value Indo-Pacific regional media, defense, think-tank, international-organization, or diplomatic source. Select relevant categories. |
| [UN ESCAP](https://www.unescap.org/) | International organization | Official UN | English / EN: Yes | Yes - official international/government institution | changedetection.io | — | — | Medium / Phase 2 | Asia-Pacific economy; development; data | High-value Indo-Pacific regional media, defense, think-tank, international-organization, or diplomatic source. Report-heavy. |
| [WHO Western Pacific](https://www.who.int/westernpacific) | International organization | Official UN agency | English / EN: Yes | Yes - official international/government institution | changedetection.io | — | — | Medium / Phase 2 | Health emergencies; regional public health | High-value Indo-Pacific regional media, defense, think-tank, international-organization, or diplomatic source. Site/API structure can change. |
| [World Bank East Asia & Pacific](https://www.worldbank.org/en/region/eap) | International organization | Official multilateral | English / EN: Yes | Yes - official international/government institution | changedetection.io | — | — | Medium / Phase 2 | Economy; development; country data | High-value Indo-Pacific regional media, defense, think-tank, international-organization, or diplomatic source. Low frequency/PDF-data heavy. |

## YouTube & Video Sources

| Source | Organization type | Orientation | Language / English | Official status | Ingestion | RSS / feed page | YouTube | Priority / Phase | Topics | Value / access notes |
|---|---|---|---|---|---|---|---|---|---|---|
| [Channel News Asia (Singapore)](https://www.channelnewsasia.com/) | Regional broadcaster/digital | Mainstream | English / EN: Yes | No | YouTube/yt-dlp | — | https://www.youtube.com/@channelnewsasia | Critical / Phase 1 | Southeast Asia; China; Asia; business | High-value Indo-Pacific regional media, defense, think-tank, international-organization, or diplomatic source. No broad RSS verified. |
| [Radio Free Asia](https://www.rfa.org/) | International broadcaster | U.S.-funded international broadcaster | English / EN: Yes | No | YouTube/yt-dlp | — | https://www.youtube.com/@RFAVideo | Critical / Phase 1 | China; North Korea; Southeast Asia; human rights | High-value Indo-Pacific regional media, defense, think-tank, international-organization, or diplomatic source. Blocked in target countries; language-service structures vary. |
| [Voice of America](https://www.voanews.com/) | International broadcaster | U.S.-funded international broadcaster | English / EN: Yes | No | YouTube/yt-dlp | — | https://www.youtube.com/@VOANews | High / Phase 1 | World; U.S. policy; Asia; China; Korea | High-value Indo-Pacific regional media, defense, think-tank, international-organization, or diplomatic source. Language services have separate sites/channels. |

## Other High-Value Sources

| Source | Organization type | Orientation | Language / English | Official status | Ingestion | RSS / feed page | YouTube | Priority / Phase | Topics | Value / access notes |
|---|---|---|---|---|---|---|---|---|---|---|
| [South China Morning Post](https://www.scmp.com/) | Regional newspaper | Mainstream / Hong Kong-based | English / EN: Yes | No | Direct scraping | — | — | Critical / Phase 1 | China; Hong Kong; Asia; technology; business | High-value Indo-Pacific regional media, defense, think-tank, international-organization, or diplomatic source. Paywall/anti-bot; licensed access may be preferable. |
| [The Diplomat](https://thediplomat.com/) | Regional digital magazine | Mainstream / regional affairs | English / EN: Yes | No | Native RSS | https://thediplomat.com/feed/ | — | Critical / Phase 1 | Asia-Pacific politics; defense; diplomacy | High-value Indo-Pacific regional media, defense, think-tank, international-organization, or diplomatic source. Some premium content. |
| [Asia Times](https://asiatimes.com/) | Regional digital publication | Mixed / analysis-heavy | English / EN: Yes | No | Native RSS | https://asiatimes.com/feed/ | — | High / Phase 2 | China; Asia security; economy; geopolitics | High-value Indo-Pacific regional media, defense, think-tank, international-organization, or diplomatic source. Contributor quality varies; tag analysis/opinion. |
| [The Straits Times](https://www.straitstimes.com/) | Regional newspaper | Mainstream | English / EN: Yes | No | Direct scraping | — | — | High / Phase 1 | Southeast Asia; China; Asia; business | High-value Indo-Pacific regional media, defense, think-tank, international-organization, or diplomatic source. Paywall on many stories. |

# Recommended Phase 1 — First 190 Sources

Phase 1 is deliberately capped at 190 sources, inside the requested 100–200 range. It balances countries and mixes easy native feeds with a controlled number of critical government, defense, court, election, YouTube, and hard-source targets so the platform proves every ingestion path without making the first sprint unmanageable.

## United States (35)

- **Breaking Defense** — Critical — Native RSS — https://breakingdefense.com/
- **CISA** — Critical — Native RSS — https://www.cisa.gov/
- **CSIS** — Critical — Native RSS — https://www.csis.org/
- **Congress.gov** — Critical — Native RSS — https://www.congress.gov/
- **Defense News** — Critical — Native RSS — https://www.defensenews.com/
- **Department of Justice** — Critical — Native RSS — https://www.justice.gov/
- **Federal Register** — Critical — Native RSS — https://www.federalregister.gov/
- **Politico** — Critical — Native RSS — https://www.politico.com/
- **SCOTUSblog** — Critical — Native RSS — https://www.scotusblog.com/
- **The New York Times** — Critical — Native RSS — https://www.nytimes.com/
- **The Washington Post** — Critical — Native RSS — https://www.washingtonpost.com/
- **U.S. Department of Defense** — Critical — Native RSS — https://www.defense.gov/
- **USNI News** — Critical — Native RSS — https://news.usni.org/
- **U.S. Navy** — Critical — YouTube/yt-dlp — https://www.navy.mil/
- **Supreme Court of the United States** — Critical — changedetection.io — https://www.supremecourt.gov/
- **U.S. Department of State** — Critical — changedetection.io — https://www.state.gov/
- **U.S. Indo-Pacific Command** — Critical — changedetection.io — https://www.pacom.mil/
- **White House** — Critical — changedetection.io — https://www.whitehouse.gov/
- **Asia Maritime Transparency Initiative (CSIS)** — Critical — Direct scraping — https://amti.csis.org/
- **Associated Press (AP)** — Critical — Direct scraping — https://apnews.com/
- **Beyond Parallel (CSIS)** — Critical — Direct scraping — https://beyondparallel.csis.org/
- **Bloomberg** — Critical — Direct scraping — https://www.bloomberg.com/
- **Reuters U.S.** — Critical — Direct scraping — https://www.reuters.com/world/us/
- **The Wall Street Journal** — Critical — Direct scraping — https://www.wsj.com/
- **ABC News** — High — Native RSS — https://abcnews.go.com/
- **CBS News** — High — Native RSS — https://www.cbsnews.com/
- **CNN** — High — Native RSS — https://www.cnn.com/
- **Department of Homeland Security** — High — Native RSS — https://www.dhs.gov/
- **Federal Bureau of Investigation** — High — Native RSS — https://www.fbi.gov/
- **Fox News** — High — Native RSS — https://www.foxnews.com/
- **NBC News** — High — Native RSS — https://www.nbcnews.com/
- **U.S. Air Force** — High — YouTube/yt-dlp — https://www.af.mil/
- **U.S. Army** — High — YouTube/yt-dlp — https://www.army.mil/
- **U.S. Coast Guard** — High — YouTube/yt-dlp — https://www.uscg.mil/
- **U.S. Marine Corps** — High — YouTube/yt-dlp — https://www.marines.mil/

## South Korea (30)

- **Electronic Times (전자신문)** — Critical — Native RSS — https://www.etnews.com/
- **KBS World Radio News** — Critical — Native RSS — https://world.kbs.co.kr/
- **Maeil Business Newspaper (매일경제)** — Critical — Native RSS — https://www.mk.co.kr/
- **National Election Commission (중앙선거관리위원회)** — Critical — Native RSS — https://www.nec.go.kr/
- **Newsis (뉴시스)** — Critical — Native RSS — https://www.newsis.com/
- **SBS News** — Critical — Native RSS — https://news.sbs.co.kr/
- **KBS News** — Critical — YouTube/yt-dlp — https://news.kbs.co.kr/
- **MBC News** — Critical — YouTube/yt-dlp — https://news.mbc.co.kr/
- **Newstapa (뉴스타파)** — Critical — YouTube/yt-dlp — https://newstapa.org/
- **YTN** — Critical — YouTube/yt-dlp — https://www.ytn.co.kr/
- **뉴스타파** — Critical — YouTube/yt-dlp — https://www.youtube.com/@newstapa
- **Constitutional Court of Korea (헌법재판소)** — Critical — changedetection.io — https://www.ccourt.go.kr/
- **Ministry of Foreign Affairs (외교부)** — Critical — changedetection.io — https://www.mofa.go.kr/
- **Ministry of National Defense (국방부)** — Critical — changedetection.io — https://www.mnd.go.kr/
- **Ministry of Unification (통일부)** — Critical — changedetection.io — https://www.unikorea.go.kr/
- **National Assembly (대한민국 국회)** — Critical — changedetection.io — https://www.assembly.go.kr/
- **Office of the President (대통령실)** — Critical — changedetection.io — https://www.president.go.kr/
- **ROK Joint Chiefs of Staff (합동참모본부)** — Critical — changedetection.io — https://www.jcs.mil.kr/
- **Supreme Court of Korea (대한민국 법원)** — Critical — changedetection.io — https://www.scourt.go.kr/
- **Boannews (보안뉴스)** — Critical — Direct scraping — https://www.boannews.com/
- **Chosun Ilbo (조선일보)** — Critical — Direct scraping — https://www.chosun.com/
- **Dong-A Ilbo (동아일보)** — Critical — Direct scraping — https://www.donga.com/
- **Hankyoreh (한겨레)** — Critical — Direct scraping — https://www.hani.co.kr/
- **Korea Policy Briefing (정책브리핑)** — Critical — Direct scraping — https://www.korea.kr/
- **Yonhap News Agency (연합뉴스)** — Critical — Direct scraping — https://www.yna.co.kr/
- **JoongAng Ilbo (중앙일보)** — Critical — Playwright — https://www.joongang.co.kr/
- **Asan Institute for Policy Studies** — High — Native RSS — https://www.asaninst.org/
- **BusinessKorea** — High — Native RSS — https://www.businesskorea.co.kr/
- **Kyunghyang Shinmun (경향신문)** — High — Native RSS — https://www.khan.co.kr/
- **OhmyNews (오마이뉴스)** — High — Native RSS — https://www.ohmynews.com/

## Japan (25)

- **Cabinet Office (内閣府)** — Critical — Native RSS — https://www.cao.go.jp/
- **Ministry of Defense (防衛省)** — Critical — Native RSS — https://www.mod.go.jp/
- **Prime Minister's Office (Kantei / 首相官邸)** — Critical — Native RSS — https://www.kantei.go.jp/
- **Ryukyu Shimpo (琉球新報)** — Critical — Native RSS — https://ryukyushimpo.jp/
- **Japan Air Self-Defense Force (航空自衛隊)** — Critical — YouTube/yt-dlp — https://www.mod.go.jp/asdf/
- **Japan Joint Staff (統合幕僚監部)** — Critical — YouTube/yt-dlp — https://www.mod.go.jp/js/
- **Japan Maritime Self-Defense Force (海上自衛隊)** — Critical — YouTube/yt-dlp — https://www.mod.go.jp/msdf/
- **Cabinet Secretariat (内閣官房)** — Critical — changedetection.io — https://www.cas.go.jp/
- **House of Councillors (参議院)** — Critical — changedetection.io — https://www.sangiin.go.jp/
- **House of Representatives (衆議院)** — Critical — changedetection.io — https://www.shugiin.go.jp/
- **Japan Coast Guard (海上保安庁)** — Critical — changedetection.io — https://www.kaiho.mlit.go.jp/
- **Ministry of Foreign Affairs of Japan (MOFA)** — Critical — changedetection.io — https://www.mofa.go.jp/
- **Ministry of Internal Affairs and Communications (MIC)** — Critical — changedetection.io — https://www.soumu.go.jp/
- **National Institute for Defense Studies (NIDS)** — Critical — changedetection.io — https://www.nids.mod.go.jp/
- **Supreme Court of Japan / Courts** — Critical — changedetection.io — https://www.courts.go.jp/
- **Jiji Press (時事通信)** — Critical — Direct scraping — https://www.jiji.com/
- **Kyodo News (共同通信)** — Critical — Direct scraping — https://www.kyodo.co.jp/
- **NHK News Web** — Critical — Direct scraping — https://www3.nhk.or.jp/news/
- **Nikkei (日本経済新聞)** — Critical — Direct scraping — https://www.nikkei.com/
- **Nikkei Asia** — Critical — Direct scraping — https://asia.nikkei.com/
- **Security NEXT** — Critical — Direct scraping — https://www.security-next.com/
- **Yomiuri Shimbun (読売新聞)** — Critical — Direct scraping — https://www.yomiuri.co.jp/
- **Asahi Shimbun (朝日新聞)** — Critical — Playwright — https://www.asahi.com/
- **Okinawa Times (沖縄タイムス)** — Critical — Playwright — https://www.okinawatimes.co.jp/
- **Sankei Shimbun (産経新聞)** — Critical — Playwright — https://www.sankei.com/

## Taiwan (22)

- **Central News Agency (中央通訊社 / CNA)** — Critical — Native RSS — https://www.cna.com.tw/
- **Liberty Times (自由時報)** — Critical — Native RSS — https://www.ltn.com.tw/
- **Mainland Affairs Council (大陸委員會)** — Critical — Native RSS — https://www.mac.gov.tw/
- **Ministry of Foreign Affairs (外交部)** — Critical — Native RSS — https://www.mofa.gov.tw/
- **Office of the President, Republic of China (Taiwan)** — Critical — Native RSS — https://www.president.gov.tw/
- **Public Television Service (公視 / PTS)** — Critical — Native RSS — https://news.pts.org.tw/
- **Administration for Cyber Security, MODA** — Critical — changedetection.io — https://moda.gov.tw/ACS/
- **Central Election Commission (中央選舉委員會)** — Critical — changedetection.io — https://www.cec.gov.tw/
- **Coast Guard Administration (海巡署)** — Critical — changedetection.io — https://www.cga.gov.tw/
- **Constitutional Court (憲法法庭)** — Critical — changedetection.io — https://cons.judicial.gov.tw/
- **Executive Yuan (行政院)** — Critical — changedetection.io — https://www.ey.gov.tw/
- **Judicial Yuan (司法院)** — Critical — changedetection.io — https://www.judicial.gov.tw/
- **Legislative Yuan (立法院)** — Critical — changedetection.io — https://www.ly.gov.tw/
- **Ministry of National Defense (國防部)** — Critical — changedetection.io — https://www.mnd.gov.tw/
- **China Times (中國時報)** — Critical — Direct scraping — https://www.chinatimes.com/
- **DigiTimes** — Critical — Direct scraping — https://www.digitimes.com/
- **Institute for National Defense and Security Research (INDSR)** — Critical — Direct scraping — https://indsr.org.tw/
- **The Reporter (報導者)** — Critical — Direct scraping — https://www.twreporter.org/
- **United Daily News (聯合新聞網 / UDN)** — Critical — Direct scraping — https://udn.com/
- **iThome** — Critical — Direct scraping — https://www.ithome.com.tw/
- **Taipei Times** — High — Native RSS — https://www.taipeitimes.com/
- **TechNews 科技新報** — High — Native RSS — https://technews.tw/

## China (25)

- **China Digital Times** — Critical — Native RSS — https://chinadigitaltimes.net/
- **China Media Project** — Critical — Native RSS — https://chinamediaproject.org/
- **CCTV News / 央视新闻** — Critical — YouTube/yt-dlp — https://news.cctv.com/
- **CGTN** — Critical — YouTube/yt-dlp — https://www.cgtn.com/
- **Xinhua News Agency (新华社)** — Critical — YouTube/yt-dlp — https://www.news.cn/
- **China Coast Guard (中国海警局)** — Critical — changedetection.io — https://www.ccg.gov.cn/
- **Cyberspace Administration of China (国家互联网信息办公室)** — Critical — changedetection.io — https://www.cac.gov.cn/
- **Ministry of Foreign Affairs (外交部)** — Critical — changedetection.io — https://www.mfa.gov.cn/
- **Ministry of National Defense (国防部)** — Critical — changedetection.io — http://www.mod.gov.cn/
- **National People's Congress (全国人大)** — Critical — changedetection.io — http://www.npc.gov.cn/
- **State Council of the PRC (中国政府网)** — Critical — changedetection.io — https://www.gov.cn/
- **Supreme People's Court (最高人民法院)** — Critical — changedetection.io — https://www.court.gov.cn/
- **Taiwan Affairs Office of the State Council (国台办)** — Critical — changedetection.io — https://www.gwytb.gov.cn/
- **Caixin (财新)** — Critical — Direct scraping — https://www.caixin.com/
- **FreeBuf** — Critical — Direct scraping — https://www.freebuf.com/
- **Global Times (环球时报)** — Critical — Direct scraping — https://www.globaltimes.cn/
- **PLA Daily / China Military Online (解放军报/中国军网)** — Critical — Direct scraping — http://www.81.cn/
- **People's Daily (人民日报)** — Critical — Direct scraping — http://www.people.com.cn/
- **What's on Weibo** — High — Native RSS — https://www.whatsonweibo.com/
- **China Daily** — High — YouTube/yt-dlp — https://www.chinadaily.com.cn/
- **Supreme People's Procuratorate (最高人民检察院)** — High — changedetection.io — https://www.spp.gov.cn/
- **China News Service (中国新闻网)** — High — Direct scraping — https://www.chinanews.com.cn/
- **Yicai / First Financial (第一财经)** — High — Direct scraping — https://www.yicai.com/
- **36Kr (36氪)** — High — Playwright — https://36kr.com/
- **The Paper (澎湃新闻)** — High — Playwright — https://www.thepaper.cn/

## North Korea / DPRK Monitoring (15)

- **38 North** — Critical — Native RSS — https://www.38north.org/
- **Daily NK** — Critical — Native RSS — https://www.dailynk.com/
- **DPRK Ministry of Foreign Affairs** — Critical — changedetection.io — http://www.mfa.gov.kp/
- **International Atomic Energy Agency (IAEA) - DPRK** — Critical — changedetection.io — https://www.iaea.org/topics/dprk
- **North Korea Information Portal (Unification Ministry)** — Critical — changedetection.io — https://nkinfo.unikorea.go.kr/
- **UN Security Council DPRK Sanctions Committee (1718)** — Critical — changedetection.io — https://main.un.org/securitycouncil/en/sanctions/1718
- **CSIS Beyond Parallel** — Critical — Direct scraping — https://beyondparallel.csis.org/
- **Korean Central News Agency (KCNA)** — Critical — Direct scraping — http://www.kcna.kp/
- **NK News** — Critical — Direct scraping — https://www.nknews.org/
- **Rodong Sinmun (로동신문)** — Critical — Direct scraping — http://www.rodong.rep.kp/
- **NK Leadership Watch** — High — Native RSS — https://www.nkleadershipwatch.org/
- **North Korea Tech** — High — Native RSS — https://www.northkoreatech.org/
- **UN Human Rights Office - DPRK** — High — changedetection.io — https://seoul.ohchr.org/en
- **Naenara** — High — Direct scraping — http://www.naenara.com.kp/
- **Voice of Korea** — High — Direct scraping — http://www.vok.rep.kp/

## Philippines (20)

- **ABS-CBN News** — Critical — Native RSS — https://www.abs-cbn.com/news
- **BusinessWorld** — Critical — Native RSS — https://www.bworldonline.com/
- **GMA News Online** — Critical — Native RSS — https://www.gmanetwork.com/news/
- **Philippine Center for Investigative Journalism (PCIJ)** — Critical — Native RSS — https://pcij.org/
- **Philippine Daily Inquirer / Inquirer.net** — Critical — Native RSS — https://www.inquirer.net/
- **Rappler** — Critical — Native RSS — https://www.rappler.com/
- **VERA Files** — Critical — Native RSS — https://verafiles.org/
- **Radio Television Malacañang (RTVM)** — Critical — YouTube/yt-dlp — https://rtvm.gov.ph/
- **Armed Forces of the Philippines (AFP)** — Critical — changedetection.io — https://www.afp.mil.ph/
- **Department of Foreign Affairs (DFA)** — Critical — changedetection.io — https://dfa.gov.ph/
- **Department of National Defense (DND)** — Critical — changedetection.io — https://www.dnd.gov.ph/
- **House of Representatives of the Philippines** — Critical — changedetection.io — https://www.congress.gov.ph/
- **National Security Council of the Philippines** — Critical — changedetection.io — https://nsc.gov.ph/
- **Philippine Coast Guard** — Critical — changedetection.io — https://coastguard.gov.ph/
- **Philippine Navy** — Critical — changedetection.io — https://www.navy.mil.ph/
- **Presidential Communications Office (PCO)** — Critical — changedetection.io — https://pco.gov.ph/
- **Supreme Court of the Philippines** — Critical — changedetection.io — https://sc.judiciary.gov.ph/
- **Philippine News Agency (PNA)** — Critical — Direct scraping — https://www.pna.gov.ph/
- **Office of the President of the Philippines** — Critical — Playwright — https://president.gov.ph/
- **Official Gazette of the Republic of the Philippines** — Critical — Playwright — https://www.officialgazette.gov.ph/

## Indo-Pacific / Regional (18)

- **Naval News** — Critical — Native RSS — https://www.navalnews.com/
- **The Diplomat** — Critical — Native RSS — https://thediplomat.com/
- **USNI News** — Critical — Native RSS — https://news.usni.org/
- **Channel News Asia (Singapore)** — Critical — YouTube/yt-dlp — https://www.channelnewsasia.com/
- **Radio Free Asia** — Critical — YouTube/yt-dlp — https://www.rfa.org/
- **American Institute in Taiwan (AIT)** — Critical — changedetection.io — https://www.ait.org.tw/
- **U.S. Embassy Manila** — Critical — changedetection.io — https://ph.usembassy.gov/
- **International Institute for Strategic Studies (IISS)** — Critical — Direct scraping — https://www.iiss.org/
- **Janes** — Critical — Direct scraping — https://www.janes.com/
- **South China Morning Post** — Critical — Direct scraping — https://www.scmp.com/
- **ASPI / The Strategist** — High — Native RSS — https://www.aspistrategist.org.au/
- **International Atomic Energy Agency (IAEA)** — High — Native RSS — https://www.iaea.org/
- **Lowy Institute / The Interpreter** — High — Native RSS — https://www.lowyinstitute.org/the-interpreter
- **Voice of America** — High — YouTube/yt-dlp — https://www.voanews.com/
- **ASEAN** — High — changedetection.io — https://asean.org/
- **UN Security Council** — High — changedetection.io — https://main.un.org/securitycouncil/
- **BenarNews** — High — Direct scraping — https://www.benarnews.org/
- **The Straits Times** — High — Direct scraping — https://www.straitstimes.com/

# Recommended Phase 2 Expansion

Phase 2 expands regional depth, ideological diversity, additional business/technology outlets, second-tier agencies, research centers, and technically harder/paywalled sources after Phase 1 source health, deduplication, and rights policies are stable.

## United States (42)

- **Axios** — High — Direct scraping — https://www.axios.com/
- **Breitbart News** — High — Native RSS — https://www.breitbart.com/
- **Carnegie Endowment** — High — Direct scraping — https://carnegieendowment.org/
- **Center for a New American Security** — High — Direct scraping — https://www.cnas.org/
- **Central Intelligence Agency** — High — changedetection.io — https://www.cia.gov/
- **ChinaPower Project (CSIS)** — High — Direct scraping — https://chinapower.csis.org/
- **Council on Foreign Relations** — High — Native RSS — https://www.cfr.org/
- **Defense One** — High — Direct scraping — https://www.defenseone.com/
- **Federal News Network** — High — Native RSS — https://federalnewsnetwork.com/
- **Foreign Affairs** — High — Direct scraping — https://www.foreignaffairs.com/
- **Foreign Policy** — High — Direct scraping — https://foreignpolicy.com/
- **Hudson Institute** — High — Native RSS — https://www.hudson.org/
- **Just Security** — High — Native RSS — https://www.justsecurity.org/
- **Lawfare** — High — Native RSS — https://www.lawfaremedia.org/
- **NPR** — High — Native RSS — https://www.npr.org/
- **National Review** — High — Native RSS — https://www.nationalreview.com/
- **National Security Agency** — High — changedetection.io — https://www.nsa.gov/
- **Office of the Director of National Intelligence** — High — changedetection.io — https://www.dni.gov/
- **PBS NewsHour** — High — Native RSS — https://www.pbs.org/newshour/
- **ProPublica** — High — Native RSS — https://www.propublica.org/
- **RAND Corporation** — High — Native RSS — https://www.rand.org/
- **RealClearPolitics** — High — Direct scraping — https://www.realclearpolitics.com/
- **The Hill** — High — Native RSS — https://thehill.com/
- **The Intercept** — High — Native RSS — https://theintercept.com/
- **The War Zone** — High — Native RSS — https://www.twz.com/
- **U.S. Courts** — High — changedetection.io — https://www.uscourts.gov/
- **U.S. House of Representatives** — High — changedetection.io — https://www.house.gov/
- **U.S. Senate** — High — changedetection.io — https://www.senate.gov/
- **U.S. Space Force** — High — Direct scraping — https://www.spaceforce.mil/
- **USA Today** — High — Direct scraping — https://www.usatoday.com/
- **War on the Rocks** — High — Native RSS — https://warontherocks.com/
- **Washington Examiner** — High — Direct scraping — https://www.washingtonexaminer.com/
- **Atlantic Council** — Medium — Native RSS — https://www.atlanticcouncil.org/
- **Brookings Institution** — Medium — Native RSS — https://www.brookings.edu/
- **Heritage Foundation** — Medium — Native RSS — https://www.heritage.org/
- **Mother Jones** — Medium — Native RSS — https://www.motherjones.com/
- **Semafor** — Medium — Direct scraping — https://www.semafor.com/
- **Stanford APARC** — Medium — Direct scraping — https://aparc.fsi.stanford.edu/
- **The Atlantic** — Medium — Direct scraping — https://www.theatlantic.com/
- **The Daily Wire** — Medium — Direct scraping — https://www.dailywire.com/
- **The Federalist** — Medium — Native RSS — https://thefederalist.com/
- **MIT Security Studies Program** — Low — changedetection.io — https://ssp.mit.edu/

## South Korea (31)

- **Institute for National Security Strategy (INSS)** — High — Direct scraping — https://www.inss.re.kr/
- **JTBC News** — High — YouTube/yt-dlp — https://news.jtbc.co.kr/
- **Korea Economic Daily (한국경제)** — High — Direct scraping — https://www.hankyung.com/
- **Korea Institute for Defense Analyses (KIDA)** — High — Direct scraping — https://www.kida.re.kr/
- **Korea Institute for International Economic Policy (KIEP)** — High — Direct scraping — https://www.kiep.go.kr/
- **Korea Institute for National Unification (KINU)** — High — Direct scraping — https://www.kinu.or.kr/
- **Korean National Police Agency (경찰청)** — High — changedetection.io — https://www.police.go.kr/
- **National Intelligence Service (국가정보원)** — High — changedetection.io — https://www.nis.go.kr/
- **News1 Korea (뉴스1)** — High — Direct scraping — https://www.news1.kr/
- **Pennmike (펜앤드마이크)** — High — YouTube/yt-dlp — https://www.pennmike.com/
- **Republic of Korea Air Force** — High — changedetection.io — https://www.airforce.mil.kr/
- **Republic of Korea Army** — High — changedetection.io — https://www.army.mil.kr/
- **Republic of Korea Navy** — High — changedetection.io — https://www.navy.mil.kr/
- **Sejong Institute** — High — Direct scraping — https://www.sejong.org/
- **SisaIN (시사IN)** — High — Direct scraping — https://www.sisain.co.kr/
- **The Korea Herald** — High — Direct scraping — https://www.koreaherald.com/
- **The Korea Times** — High — Direct scraping — https://www.koreatimes.co.kr/
- **Yonhap News TV (연합뉴스TV)** — High — YouTube/yt-dlp — https://www.yonhapnewstv.co.kr/
- **ZDNet Korea** — High — Direct scraping — https://zdnet.co.kr/
- **김어준의 겸손은힘들다 뉴스공장** — High — YouTube/yt-dlp — https://www.youtube.com/@gyeomsonisnothing
- **신의한수** — High — YouTube/yt-dlp — https://www.youtube.com/@shinuihansu
- **오마이TV** — High — YouTube/yt-dlp — https://www.youtube.com/@OhmynewsTV
- **펜앤드마이크TV** — High — YouTube/yt-dlp — https://www.youtube.com/@pennmike
- **Dailyan (데일리안)** — Medium — Direct scraping — https://www.dailian.co.kr/
- **East Asia Institute (EAI)** — Medium — Direct scraping — https://www.eai.or.kr/
- **Korea Communications Commission** — Medium — changedetection.io — https://www.kcc.go.kr/
- **New Daily (뉴데일리)** — Medium — Direct scraping — https://www.newdaily.co.kr/
- **Pressian (프레시안)** — Medium — Direct scraping — https://www.pressian.com/
- **Seoul National University Institute for Peace and Unification Studies** — Medium — Direct scraping — https://ipus.snu.ac.kr/
- **고성국TV** — Medium — YouTube/yt-dlp — https://www.youtube.com/@kosungkuk
- **성창경TV** — Medium — YouTube/yt-dlp — https://www.youtube.com/@sungchangkyung

## Japan (28)

- **Acquisition, Technology & Logistics Agency (ATLA)** — High — changedetection.io — https://www.mod.go.jp/atla/
- **Bunshun Online (文春オンライン)** — High — Direct scraping — https://bunshun.jp/
- **Hokkaido Shimbun (北海道新聞)** — High — Direct scraping — https://www.hokkaido-np.co.jp/
- **IDE-JETRO** — High — Direct scraping — https://www.ide.go.jp/English/
- **ITmedia** — High — Direct scraping — https://www.itmedia.co.jp/
- **Institute of Geoeconomics (IOG)** — High — Direct scraping — https://instituteofgeoeconomics.org/
- **JBpress** — High — Direct scraping — https://jbpress.ismedia.jp/
- **Japan Forward** — High — Native RSS — https://japan-forward.com/
- **Japan Ground Self-Defense Force (陸上自衛隊)** — High — YouTube/yt-dlp — https://www.mod.go.jp/gsdf/
- **Japan Institute of International Affairs (JIIA)** — High — Direct scraping — https://www.jiia.or.jp/
- **Mainichi Shimbun (毎日新聞)** — High — Direct scraping — https://mainichi.jp/
- **National Police Agency (警察庁)** — High — Native RSS — https://www.npa.go.jp/
- **Nippon.com** — High — Native RSS — https://www.nippon.com/
- **Nishinippon Shimbun (西日本新聞)** — High — Direct scraping — https://www.nishinippon.co.jp/
- **Public Security Intelligence Agency (公安調査庁)** — High — changedetection.io — https://www.moj.go.jp/psia/
- **Sasakawa Peace Foundation** — High — Direct scraping — https://www.spf.org/
- **ScanNetSecurity** — High — Direct scraping — https://scan.netsecurity.ne.jp/
- **Tansa** — High — Direct scraping — https://tansajp.org/
- **The Japan Times** — High — Native RSS — https://www.japantimes.co.jp/
- **Tokyo Shimbun (東京新聞)** — High — Direct scraping — https://www.tokyo-np.co.jp/
- **Toyo Keizai Online (東洋経済オンライン)** — High — Direct scraping — https://toyokeizai.net/
- **Chunichi Shimbun (中日新聞)** — Medium — Direct scraping — https://www.chunichi.co.jp/
- **Diamond Online (ダイヤモンド・オンライン)** — Medium — Direct scraping — https://diamond.jp/
- **GRIPS Alliance / National Graduate Institute for Policy Studies** — Medium — changedetection.io — https://www.grips.ac.jp/en/
- **Kahoku Shimpo (河北新報)** — Medium — Direct scraping — https://kahoku.news/
- **Kobe Shimbun (神戸新聞)** — Medium — Direct scraping — https://www.kobe-np.co.jp/
- **Research Institute for Peace and Security (RIPS)** — Medium — changedetection.io — https://www.rips.or.jp/english/
- **University of Tokyo ROLES** — Medium — changedetection.io — https://roles.rcast.u-tokyo.ac.jp/

## Taiwan (20)

- **CommonWealth Magazine (天下雜誌)** — High — Direct scraping — https://www.cw.com.tw/
- **Doublethink Lab** — High — Direct scraping — https://doublethinklab.org/
- **Formosa TV News (民視新聞)** — High — YouTube/yt-dlp — https://www.ftvnews.com.tw/
- **Institute of International Relations, NCCU** — High — changedetection.io — https://iir.nccu.edu.tw/
- **Mirror Media (鏡週刊 / 鏡新聞)** — High — Direct scraping — https://www.mirrormedia.mg/
- **National Chung-Shan Institute of Science and Technology (NCSIST)** — High — changedetection.io — https://www.ncsist.org.tw/
- **National Police Agency (警政署)** — High — changedetection.io — https://www.npa.gov.tw/
- **National Security Bureau (國家安全局)** — High — changedetection.io — https://www.nsb.gov.tw/
- **Prospect Foundation** — High — Direct scraping — https://www.pf.org.tw/
- **SET News (三立新聞網)** — High — YouTube/yt-dlp — https://www.setn.com/
- **Storm Media (風傳媒)** — High — Direct scraping — https://www.storm.mg/
- **TVBS News** — High — YouTube/yt-dlp — https://news.tvbs.com.tw/
- **Taiwan FactCheck Center** — High — Direct scraping — https://tfc-taiwan.org.tw/
- **Taiwan News** — High — Direct scraping — https://www.taiwannews.com.tw/
- **TaiwanPlus** — High — YouTube/yt-dlp — https://www.taiwanplus.com/
- **Academia Sinica** — Medium — Direct scraping — https://www.sinica.edu.tw/en
- **EBC News (東森新聞)** — Medium — YouTube/yt-dlp — https://news.ebc.net.tw/
- **Inside** — Medium — Direct scraping — https://www.inside.com.tw/
- **New Bloom Magazine** — Medium — Native RSS — https://newbloommag.net/
- **Taiwan-Asia Exchange Foundation** — Medium — Direct scraping — https://www.taef.org/

## China (23)

- **Anquanke (安全客)** — High — Direct scraping — https://www.anquanke.com/
- **Caijing (财经)** — High — Direct scraping — https://www.caijing.com.cn/
- **China Institute of International Studies (CIIS)** — High — changedetection.io — https://www.ciis.org.cn/
- **China Institutes of Contemporary International Relations (CICIR)** — High — changedetection.io — http://www.cicir.ac.cn/
- **Economic Daily (经济日报)** — High — Direct scraping — http://www.ce.cn/
- **GreatFire.org** — High — Direct scraping — https://en.greatfire.org/
- **Jiemian News (界面新闻)** — High — Playwright — https://www.jiemian.com/
- **LatePost (晚点)** — High — Direct scraping — https://www.latepost.com/
- **Ministry of Commerce (商务部)** — High — changedetection.io — http://www.mofcom.gov.cn/
- **Ministry of Public Security (公安部)** — High — changedetection.io — https://www.mps.gov.cn/
- **National Development and Reform Commission (国家发展改革委)** — High — changedetection.io — https://www.ndrc.gov.cn/
- **Peking University Institute of International and Strategic Studies** — High — changedetection.io — https://en.iiss.pku.edu.cn/
- **People's Bank of China (中国人民银行)** — High — changedetection.io — http://www.pbc.gov.cn/
- **Shanghai Institutes for International Studies (SIIS)** — High — Direct scraping — https://www.siis.org.cn/
- **Southern Weekly (南方周末)** — High — Direct scraping — https://www.infzm.com/
- **State Administration for Market Regulation** — High — changedetection.io — https://www.samr.gov.cn/
- **The Beijing News (新京报)** — High — Direct scraping — https://www.bjnews.com.cn/
- **Tsinghua Center for International Security and Strategy** — High — changedetection.io — https://ciss.tsinghua.edu.cn/
- **Center for China and Globalization (CCG)** — Medium — Direct scraping — http://en.ccg.org.cn/
- **Chinese Academy of Social Sciences (CASS)** — Medium — changedetection.io — http://www.cass.cn/
- **Fudan University Institute of International Studies** — Medium — changedetection.io — https://iis.fudan.edu.cn/
- **Huxiu (虎嗅)** — Medium — Playwright — https://www.huxiu.com/
- **TMTPost (钛媒体)** — Medium — Direct scraping — https://www.tmtpost.com/

## North Korea / DPRK Monitoring (7)

- **Committee for Human Rights in North Korea (HRNK)** — High — Direct scraping — https://www.hrnk.org/
- **KINU DPRK Research** — High — Direct scraping — https://www.kinu.or.kr/
- **Korea Risk Group** — High — Direct scraping — https://www.korearisk.com/
- **Multilateral Sanctions Monitoring Team (MSMT)** — High — changedetection.io — https://www.state.gov/
- **NK Pro** — High — Direct scraping — https://www.nknews.org/pro/
- **Radio Free Asia Korean** — High — YouTube/yt-dlp — https://www.rfa.org/korean/
- **VOA Korean** — High — YouTube/yt-dlp — https://www.voakorea.com/

## Philippines (21)

- **Commission on Elections (COMELEC)** — Critical — Playwright — https://comelec.gov.ph/
- **Senate of the Philippines** — Critical — Playwright — https://legacy.senate.gov.ph/
- **BusinessMirror** — High — Native RSS — https://businessmirror.com.ph/
- **Manila Bulletin** — High — Direct scraping — https://mb.com.ph/
- **MindaNews** — High — Native RSS — https://mindanews.com/
- **News5 / One News** — High — YouTube/yt-dlp — https://news.tv5.com.ph/
- **Newsbytes.PH** — High — Native RSS — https://newsbytes.ph/
- **Philippine Air Force** — High — changedetection.io — https://www.paf.mil.ph/
- **Philippine Army** — High — changedetection.io — https://army.mil.ph/
- **Philippine National Police (PNP)** — High — changedetection.io — https://pnp.gov.ph/
- **Stratbase ADR Institute** — High — Direct scraping — https://adrinstitute.org/
- **SunStar** — High — Direct scraping — https://www.sunstar.com.ph/
- **The Manila Times** — High — Direct scraping — https://www.manilatimes.net/
- **The Philippine Star / Philstar.com** — High — Direct scraping — https://www.philstar.com/
- **UP Institute for Maritime Affairs and Law of the Sea** — High — changedetection.io — https://law.upd.edu.ph/
- **Ateneo Policy Center** — Medium — changedetection.io — https://ateneopolicycenter.com/
- **Bilyonaryo** — Medium — Native RSS — https://bilyonaryo.com/
- **Cebu Daily News** — Medium — Native RSS — https://cebudailynews.inquirer.net/
- **Daily Tribune** — Medium — Direct scraping — https://tribune.net.ph/
- **Mindanao Times** — Medium — Native RSS — https://mindanaotimes.com.ph/
- **National Intelligence Coordinating Agency (NICA)** — Medium — changedetection.io — https://nica.gov.ph/

## Indo-Pacific / Regional (22)

- **Asia Times** — High — Native RSS — https://asiatimes.com/
- **Asian Development Bank** — High — Native RSS — https://www.adb.org/
- **Australian National University - East Asia Forum** — High — Native RSS — https://eastasiaforum.org/
- **Financial Action Task Force (FATF)** — High — changedetection.io — https://www.fatf-gafi.org/
- **ISEAS – Yusof Ishak Institute** — High — Direct scraping — https://www.iseas.edu.sg/
- **Pacific Forum** — High — Direct scraping — https://pacforum.org/
- **RSIS** — High — Direct scraping — https://www.rsis.edu.sg/
- **Taipei Economic and Cultural Representative Office in the U.S. (TECRO)** — High — changedetection.io — https://www.roc-taiwan.org/us_en/index.html
- **U.S. Embassy Beijing** — High — changedetection.io — https://china.usembassy-china.org.cn/
- **U.S. Embassy Seoul** — High — changedetection.io — https://kr.usembassy.gov/
- **U.S. Embassy Tokyo** — High — changedetection.io — https://jp.usembassy.gov/
- **APEC** — Medium — changedetection.io — https://www.apec.org/
- **Asia Society Policy Institute** — Medium — Direct scraping — https://asiasociety.org/policy-institute
- **Asia/Pacific Group on Money Laundering (APG)** — Medium — changedetection.io — https://apgml.org/
- **East-West Center** — Medium — Direct scraping — https://www.eastwestcenter.org/
- **Embassy of Japan in the United States** — Medium — changedetection.io — https://www.us.emb-japan.go.jp/itprtop_en/index.html
- **Embassy of the Republic of Korea in the U.S.** — Medium — changedetection.io — https://overseas.mofa.go.kr/us-en/index.do
- **IMF Asia and Pacific** — Medium — changedetection.io — https://www.imf.org/en/Regions/Asia-and-Pacific
- **INTERPOL** — Medium — Native RSS — https://www.interpol.int/
- **UN ESCAP** — Medium — changedetection.io — https://www.unescap.org/
- **WHO Western Pacific** — Medium — changedetection.io — https://www.who.int/westernpacific
- **World Bank East Asia & Pacific** — Medium — changedetection.io — https://www.worldbank.org/en/region/eap

# All Sources with Native RSS as the Primary Ingestion Method

Exact feed URLs are shown when recorded. When only an RSS discovery page was verified, the discovery page is listed and endpoint harvesting is required during onboarding.

- **China — China Digital Times** — https://chinadigitaltimes.net/feed/ — Native RSS established
- **China — China Media Project** — https://chinamediaproject.org/feed/ — Native RSS established
- **China — What's on Weibo** — https://www.whatsonweibo.com/feed/ — Native RSS established
- **Indo-Pacific / Regional — ASPI / The Strategist** — https://www.aspistrategist.org.au/feed/ — Native RSS available
- **Indo-Pacific / Regional — Asia Times** — https://asiatimes.com/feed/ — Native RSS available
- **Indo-Pacific / Regional — Asian Development Bank** — https://www.adb.org/rss — Native RSS available
- **Indo-Pacific / Regional — Australian National University - East Asia Forum** — https://eastasiaforum.org/feed/ — Native RSS available
- **Indo-Pacific / Regional — INTERPOL** — https://www.interpol.int/rss — Native RSS available
- **Indo-Pacific / Regional — International Atomic Energy Agency (IAEA)** — https://www.iaea.org/feeds/topnews — Native RSS available
- **Indo-Pacific / Regional — Lowy Institute / The Interpreter** — https://www.lowyinstitute.org/the-interpreter/rss.xml — Native RSS available
- **Indo-Pacific / Regional — Naval News** — https://www.navalnews.com/feed/ — Native RSS available
- **Indo-Pacific / Regional — The Diplomat** — https://thediplomat.com/feed/ — Native RSS available
- **Indo-Pacific / Regional — USNI News** — https://news.usni.org/feed/ — Native RSS available
- **Japan — Cabinet Office (内閣府)** — https://www.cao.go.jp/rss/news.rdf — Native RSS available
- **Japan — Japan Forward** — https://japan-forward.com/feed/ — Native RSS established
- **Japan — Ministry of Defense (防衛省)** — https://www.mod.go.jp/j/press/news/ — Native RSS available
- **Japan — National Police Agency (警察庁)** — https://www.npa.go.jp/news/rss.html — Native RSS available
- **Japan — Nippon.com** — https://www.nippon.com/en/feed/ — Native RSS available
- **Japan — Prime Minister's Office (Kantei / 首相官邸)** — https://www.kantei.go.jp/jp/rss/ — Native RSS available
- **Japan — Ryukyu Shimpo (琉球新報)** — https://ryukyushimpo.jp/pages/entry-164983.html — Native RSS availability verified
- **Japan — The Japan Times** — https://www.japantimes.co.jp/feed/ — Native RSS availability indicated
- **North Korea / DPRK Monitoring — 38 North** — https://www.38north.org/feed/ — Native RSS established
- **North Korea / DPRK Monitoring — Daily NK** — https://www.dailynk.com/english/feed/ — Native RSS available for English site
- **North Korea / DPRK Monitoring — NK Leadership Watch** — https://www.nkleadershipwatch.org/feed/ — Native RSS likely/WordPress
- **North Korea / DPRK Monitoring — North Korea Tech** — https://www.northkoreatech.org/feed/ — Native RSS established
- **Philippines — ABS-CBN News** — https://www.abs-cbn.com/rss.aspx/news — Native RSS page/endpoint verified
- **Philippines — Bilyonaryo** — https://bilyonaryo.com/feed/ — Native RSS established
- **Philippines — BusinessMirror** — https://businessmirror.com.ph/feed/ — Native RSS established
- **Philippines — BusinessWorld** — https://www.bworldonline.com/feed/ — Native RSS established
- **Philippines — Cebu Daily News** — https://cebudailynews.inquirer.net/feed — Native RSS available
- **Philippines — GMA News Online** — https://www.gmanetwork.com/news/rss/ — Native RSS availability verified
- **Philippines — MindaNews** — https://mindanews.com/feed/ — Native RSS established
- **Philippines — Mindanao Times** — https://mindanaotimes.com.ph/feed/ — Native RSS established
- **Philippines — Newsbytes.PH** — https://newsbytes.ph/feed/ — Native RSS established
- **Philippines — Philippine Center for Investigative Journalism (PCIJ)** — https://pcij.org/feed/ — Native RSS established
- **Philippines — Philippine Daily Inquirer / Inquirer.net** — https://newsinfo.inquirer.net/feed — Native RSS/WordPress-style feed available
- **Philippines — Rappler** — https://www.rappler.com/feed/ — Native RSS/WordPress-style endpoint; verify health
- **Philippines — VERA Files** — https://verafiles.org/feed/ — Native RSS established
- **South Korea — Asan Institute for Policy Studies** — https://www.asaninst.org/feed/ — Native RSS available
- **South Korea — BusinessKorea** — https://www.businesskorea.co.kr/rss/allArticle.xml — Native RSS available
- **South Korea — Electronic Times (전자신문)** — http://rss.etnews.com/Section901.xml — Native RSS verified
- **South Korea — KBS World Radio News** — http://world.kbs.co.kr/rss/rss_news.htm?lang=e — Native RSS verified
- **South Korea — Kyunghyang Shinmun (경향신문)** — https://www.khan.co.kr/rss/rssdata/total_news.xml — Native RSS verified
- **South Korea — Maeil Business Newspaper (매일경제)** — https://www.mk.co.kr/rss/30000001/ — Native RSS verified
- **South Korea — National Election Commission (중앙선거관리위원회)** — https://app.newsloth.com/nec-go-kr/WlpSWlc.rss — Native RSS verified via third-party feed service
- **South Korea — Newsis (뉴시스)** — https://www.newsis.com/RSS/sokbo.xml — Native RSS verified
- **South Korea — OhmyNews (오마이뉴스)** — https://rss.ohmynews.com/rss/ohmynews.xml — Native RSS verified
- **South Korea — SBS News** — https://news.sbs.co.kr/news/headlineRssFeed.do?plink=RSSREADER — Native RSS verified
- **Taiwan — Central News Agency (中央通訊社 / CNA)** — https://feeds.feedburner.com/rsscna/politics — Native RSS verified
- **Taiwan — Liberty Times (自由時報)** — https://news.ltn.com.tw/rss/all.xml — Native RSS verified
- **Taiwan — Mainland Affairs Council (大陸委員會)** — https://www.mac.gov.tw/RSS.aspx?n=1FDDB0BEA67BC1D9 — Native RSS availability verified
- **Taiwan — Ministry of Foreign Affairs (外交部)** — https://www.mofa.gov.tw/RSS.aspx — Native RSS availability verified
- **Taiwan — New Bloom Magazine** — https://newbloommag.net/feed/ — Native RSS established
- **Taiwan — Office of the President, Republic of China (Taiwan)** — https://www.president.gov.tw/Page/23 — Native RSS availability verified
- **Taiwan — Public Television Service (公視 / PTS)** — https://about.pts.org.tw/rss/index.html — Native RSS availability verified
- **Taiwan — Taipei Times** — https://www.taipeitimes.com/xml/index.rss — Native RSS likely/established
- **Taiwan — TechNews 科技新報** — https://technews.tw/feed/ — Native RSS established
- **United States — ABC News** — https://abcnews.go.com/abcnews/topstories — Native RSS availability verified
- **United States — Atlantic Council** — https://www.atlanticcouncil.org/feed/ — Native RSS available
- **United States — Breaking Defense** — https://breakingdefense.com/feed/ — Native RSS available
- **United States — Breitbart News** — https://www.breitbart.com/feed/ — Native RSS established
- **United States — Brookings Institution** — https://www.brookings.edu/feed/ — Native RSS available
- **United States — CBS News** — https://www.cbsnews.com/latest/rss/main — Native RSS availability verified
- **United States — CISA** — https://www.cisa.gov/news.xml — Native RSS available
- **United States — CNN** — http://rss.cnn.com/rss/edition.rss — Legacy native RSS; verify health
- **United States — CSIS** — https://www.csis.org/rss.xml — Native RSS available
- **United States — Congress.gov** — https://www.congress.gov/rss — Native RSS available
- **United States — Council on Foreign Relations** — https://www.cfr.org/rss.xml — Native RSS available
- **United States — Defense News** — https://www.defensenews.com/rss/ — Native RSS available
- **United States — Department of Homeland Security** — https://www.dhs.gov/news/rss — Native RSS available
- **United States — Department of Justice** — https://www.justice.gov/feeds/press_releases.xml — Native RSS available
- **United States — Federal Bureau of Investigation** — https://www.fbi.gov/feeds/fbi-in-the-news/rss.xml — Native RSS available
- **United States — Federal News Network** — https://federalnewsnetwork.com/feed/ — Native RSS established
- **United States — Federal Register** — https://www.federalregister.gov/documents/search.rss — Native RSS available
- **United States — Fox News** — https://moxie.foxnews.com/google-publisher/latest.xml — Native XML feed available
- **United States — Heritage Foundation** — https://www.heritage.org/rss — Native RSS available
- **United States — Hudson Institute** — https://www.hudson.org/rss.xml — Native RSS available
- **United States — Just Security** — https://www.justsecurity.org/feed/ — Native RSS established
- **United States — Lawfare** — https://www.lawfaremedia.org/rss.xml — Native RSS established
- **United States — Mother Jones** — https://www.motherjones.com/feed/ — Native RSS established
- **United States — NBC News** — https://feeds.nbcnews.com/nbcnews/public/news — Native RSS established
- **United States — NPR** — https://feeds.npr.org/1001/rss.xml — Native RSS established
- **United States — National Review** — https://www.nationalreview.com/feed/ — Native RSS established
- **United States — PBS NewsHour** — https://www.pbs.org/newshour/feeds/rss/headlines — Native RSS established
- **United States — Politico** — https://www.politico.com/rss/politicopicks.xml — Native RSS established
- **United States — ProPublica** — https://feeds.propublica.org/propublica/main — Native RSS established
- **United States — RAND Corporation** — https://www.rand.org/pubs.rss — Native RSS available
- **United States — SCOTUSblog** — https://www.scotusblog.com/feed/ — Native RSS established
- **United States — The Federalist** — https://thefederalist.com/feed/ — Native RSS established
- **United States — The Hill** — https://thehill.com/news/feed/ — Native RSS established
- **United States — The Intercept** — https://theintercept.com/feed/?rss — Native RSS established
- **United States — The New York Times** — https://rss.nytimes.com/services/xml/rss/nyt/HomePage.xml — Native RSS verified/established
- **United States — The War Zone** — https://www.twz.com/feed — Native RSS available
- **United States — The Washington Post** — https://www.washingtonpost.com/rss/ — Native RSS availability verified
- **United States — U.S. Department of Defense** — https://www.defense.gov/DesktopModules/ArticleCS/RSS.ashx?ContentType=400&Site=945&Category=Press%20Releases — Native RSS available
- **United States — USNI News** — https://news.usni.org/feed — Native RSS available
- **United States — War on the Rocks** — https://warontherocks.com/feed/ — Native RSS available

# Sources Recommended for RSSHub or RSS-Bridge Evaluation

These are **candidates**, not claims that a maintained RSSHub route already exists for every site. The implementation sequence should be: check for a maintained RSSHub route; otherwise prototype RSS-Bridge/custom bridge against the listing page; if the site is JS/WAF-heavy, keep the primary direct-scrape or Playwright adapter instead of building a brittle feed wrapper.

- **China — 36Kr (36氪)** — RSS-Bridge/custom bridge only if listing HTML can be fetched without browser; otherwise keep Playwright — https://36kr.com/
- **China — Anquanke (安全客)** — RSSHub if a maintained route exists; otherwise RSS-Bridge/custom bridge — https://www.anquanke.com/
- **China — Caijing (财经)** — RSSHub if a maintained route exists; otherwise RSS-Bridge/custom bridge — https://www.caijing.com.cn/
- **China — Caixin (财新)** — RSSHub if a maintained route exists; otherwise RSS-Bridge/custom bridge — https://www.caixin.com/
- **China — Center for China and Globalization (CCG)** — RSSHub if a maintained route exists; otherwise RSS-Bridge/custom bridge — http://en.ccg.org.cn/
- **China — FreeBuf** — RSSHub if a maintained route exists; otherwise RSS-Bridge/custom bridge — https://www.freebuf.com/
- **China — Global Times (环球时报)** — RSSHub if a maintained route exists; otherwise RSS-Bridge/custom bridge — https://www.globaltimes.cn/
- **China — GreatFire.org** — RSSHub if a maintained route exists; otherwise RSS-Bridge/custom bridge — https://en.greatfire.org/
- **China — Huxiu (虎嗅)** — RSS-Bridge/custom bridge only if listing HTML can be fetched without browser; otherwise keep Playwright — https://www.huxiu.com/
- **China — Jiemian News (界面新闻)** — RSS-Bridge/custom bridge only if listing HTML can be fetched without browser; otherwise keep Playwright — https://www.jiemian.com/
- **China — LatePost (晚点)** — RSSHub if a maintained route exists; otherwise RSS-Bridge/custom bridge — https://www.latepost.com/
- **China — Southern Weekly (南方周末)** — RSSHub if a maintained route exists; otherwise RSS-Bridge/custom bridge — https://www.infzm.com/
- **China — TMTPost (钛媒体)** — RSSHub if a maintained route exists; otherwise RSS-Bridge/custom bridge — https://www.tmtpost.com/
- **China — The Beijing News (新京报)** — RSSHub if a maintained route exists; otherwise RSS-Bridge/custom bridge — https://www.bjnews.com.cn/
- **China — The Paper (澎湃新闻)** — RSS-Bridge/custom bridge only if listing HTML can be fetched without browser; otherwise keep Playwright — https://www.thepaper.cn/
- **China — Yicai / First Financial (第一财经)** — RSSHub if a maintained route exists; otherwise RSS-Bridge/custom bridge — https://www.yicai.com/
- **Indo-Pacific / Regional — Asia Society Policy Institute** — RSSHub if a maintained route exists; otherwise RSS-Bridge/custom bridge — https://asiasociety.org/policy-institute
- **Indo-Pacific / Regional — BenarNews** — RSSHub if a maintained route exists; otherwise RSS-Bridge/custom bridge — https://www.benarnews.org/
- **Indo-Pacific / Regional — East-West Center** — RSSHub if a maintained route exists; otherwise RSS-Bridge/custom bridge — https://www.eastwestcenter.org/
- **Indo-Pacific / Regional — ISEAS – Yusof Ishak Institute** — RSSHub if a maintained route exists; otherwise RSS-Bridge/custom bridge — https://www.iseas.edu.sg/
- **Indo-Pacific / Regional — International Institute for Strategic Studies (IISS)** — RSSHub if a maintained route exists; otherwise RSS-Bridge/custom bridge — https://www.iiss.org/
- **Indo-Pacific / Regional — Pacific Forum** — RSSHub if a maintained route exists; otherwise RSS-Bridge/custom bridge — https://pacforum.org/
- **Indo-Pacific / Regional — RSIS** — RSSHub if a maintained route exists; otherwise RSS-Bridge/custom bridge — https://www.rsis.edu.sg/
- **Japan — Asahi Shimbun (朝日新聞)** — RSS-Bridge/custom bridge only if listing HTML can be fetched without browser; otherwise keep Playwright — https://www.asahi.com/
- **Japan — Bunshun Online (文春オンライン)** — RSSHub if a maintained route exists; otherwise RSS-Bridge/custom bridge — https://bunshun.jp/
- **Japan — Chunichi Shimbun (中日新聞)** — RSSHub if a maintained route exists; otherwise RSS-Bridge/custom bridge — https://www.chunichi.co.jp/
- **Japan — Diamond Online (ダイヤモンド・オンライン)** — RSSHub if a maintained route exists; otherwise RSS-Bridge/custom bridge — https://diamond.jp/
- **Japan — Hokkaido Shimbun (北海道新聞)** — RSSHub if a maintained route exists; otherwise RSS-Bridge/custom bridge — https://www.hokkaido-np.co.jp/
- **Japan — ITmedia** — RSSHub if a maintained route exists; otherwise RSS-Bridge/custom bridge — https://www.itmedia.co.jp/
- **Japan — Institute of Geoeconomics (IOG)** — RSSHub if a maintained route exists; otherwise RSS-Bridge/custom bridge — https://instituteofgeoeconomics.org/
- **Japan — JBpress** — RSSHub if a maintained route exists; otherwise RSS-Bridge/custom bridge — https://jbpress.ismedia.jp/
- **Japan — Japan Institute of International Affairs (JIIA)** — RSSHub if a maintained route exists; otherwise RSS-Bridge/custom bridge — https://www.jiia.or.jp/
- **Japan — Jiji Press (時事通信)** — RSSHub if a maintained route exists; otherwise RSS-Bridge/custom bridge — https://www.jiji.com/
- **Japan — Kahoku Shimpo (河北新報)** — RSSHub if a maintained route exists; otherwise RSS-Bridge/custom bridge — https://kahoku.news/
- **Japan — Kobe Shimbun (神戸新聞)** — RSSHub if a maintained route exists; otherwise RSS-Bridge/custom bridge — https://www.kobe-np.co.jp/
- **Japan — Kyodo News (共同通信)** — RSSHub if a maintained route exists; otherwise RSS-Bridge/custom bridge — https://www.kyodo.co.jp/
- **Japan — Mainichi Shimbun (毎日新聞)** — RSSHub if a maintained route exists; otherwise RSS-Bridge/custom bridge — https://mainichi.jp/
- **Japan — NHK News Web** — RSSHub if a maintained route exists; otherwise RSS-Bridge/custom bridge — https://www3.nhk.or.jp/news/
- **Japan — Nikkei (日本経済新聞)** — RSSHub if a maintained route exists; otherwise RSS-Bridge/custom bridge — https://www.nikkei.com/
- **Japan — Nikkei Asia** — RSSHub if a maintained route exists; otherwise RSS-Bridge/custom bridge — https://asia.nikkei.com/
- **Japan — Nishinippon Shimbun (西日本新聞)** — RSSHub if a maintained route exists; otherwise RSS-Bridge/custom bridge — https://www.nishinippon.co.jp/
- **Japan — Okinawa Times (沖縄タイムス)** — RSS-Bridge/custom bridge only if listing HTML can be fetched without browser; otherwise keep Playwright — https://www.okinawatimes.co.jp/
- **Japan — Sankei Shimbun (産経新聞)** — RSS-Bridge/custom bridge only if listing HTML can be fetched without browser; otherwise keep Playwright — https://www.sankei.com/
- **Japan — Sasakawa Peace Foundation** — RSSHub if a maintained route exists; otherwise RSS-Bridge/custom bridge — https://www.spf.org/
- **Japan — ScanNetSecurity** — RSSHub if a maintained route exists; otherwise RSS-Bridge/custom bridge — https://scan.netsecurity.ne.jp/
- **Japan — Security NEXT** — RSSHub if a maintained route exists; otherwise RSS-Bridge/custom bridge — https://www.security-next.com/
- **Japan — Tansa** — RSSHub if a maintained route exists; otherwise RSS-Bridge/custom bridge — https://tansajp.org/
- **Japan — Tokyo Shimbun (東京新聞)** — RSSHub if a maintained route exists; otherwise RSS-Bridge/custom bridge — https://www.tokyo-np.co.jp/
- **Japan — Toyo Keizai Online (東洋経済オンライン)** — RSSHub if a maintained route exists; otherwise RSS-Bridge/custom bridge — https://toyokeizai.net/
- **Japan — Yomiuri Shimbun (読売新聞)** — RSSHub if a maintained route exists; otherwise RSS-Bridge/custom bridge — https://www.yomiuri.co.jp/
- **North Korea / DPRK Monitoring — CSIS Beyond Parallel** — RSSHub if a maintained route exists; otherwise RSS-Bridge/custom bridge — https://beyondparallel.csis.org/
- **North Korea / DPRK Monitoring — Committee for Human Rights in North Korea (HRNK)** — RSSHub if a maintained route exists; otherwise RSS-Bridge/custom bridge — https://www.hrnk.org/
- **North Korea / DPRK Monitoring — KINU DPRK Research** — RSSHub if a maintained route exists; otherwise RSS-Bridge/custom bridge — https://www.kinu.or.kr/
- **North Korea / DPRK Monitoring — NK News** — RSSHub if a maintained route exists; otherwise RSS-Bridge/custom bridge — https://www.nknews.org/
- **Philippines — Daily Tribune** — RSSHub if a maintained route exists; otherwise RSS-Bridge/custom bridge — https://tribune.net.ph/
- **Philippines — Manila Bulletin** — RSSHub if a maintained route exists; otherwise RSS-Bridge/custom bridge — https://mb.com.ph/
- **Philippines — Stratbase ADR Institute** — RSSHub if a maintained route exists; otherwise RSS-Bridge/custom bridge — https://adrinstitute.org/
- **Philippines — SunStar** — RSSHub if a maintained route exists; otherwise RSS-Bridge/custom bridge — https://www.sunstar.com.ph/
- **Philippines — The Manila Times** — RSSHub if a maintained route exists; otherwise RSS-Bridge/custom bridge — https://www.manilatimes.net/
- **Philippines — The Philippine Star / Philstar.com** — RSSHub if a maintained route exists; otherwise RSS-Bridge/custom bridge — https://www.philstar.com/
- **South Korea — Boannews (보안뉴스)** — RSSHub if a maintained route exists; otherwise RSS-Bridge/custom bridge — https://www.boannews.com/
- **South Korea — Chosun Ilbo (조선일보)** — RSSHub if a maintained route exists; otherwise RSS-Bridge/custom bridge — https://www.chosun.com/
- **South Korea — Dong-A Ilbo (동아일보)** — RSSHub if a maintained route exists; otherwise RSS-Bridge/custom bridge — https://www.donga.com/
- **South Korea — East Asia Institute (EAI)** — RSSHub if a maintained route exists; otherwise RSS-Bridge/custom bridge — https://www.eai.or.kr/
- **South Korea — Hankyoreh (한겨레)** — RSSHub if a maintained route exists; otherwise RSS-Bridge/custom bridge — https://www.hani.co.kr/
- **South Korea — Institute for National Security Strategy (INSS)** — RSSHub if a maintained route exists; otherwise RSS-Bridge/custom bridge — https://www.inss.re.kr/
- **South Korea — JoongAng Ilbo (중앙일보)** — RSS-Bridge/custom bridge only if listing HTML can be fetched without browser; otherwise keep Playwright — https://www.joongang.co.kr/
- **South Korea — Korea Economic Daily (한국경제)** — RSSHub if a maintained route exists; otherwise RSS-Bridge/custom bridge — https://www.hankyung.com/
- **South Korea — News1 Korea (뉴스1)** — RSSHub if a maintained route exists; otherwise RSS-Bridge/custom bridge — https://www.news1.kr/
- **South Korea — Pressian (프레시안)** — RSSHub if a maintained route exists; otherwise RSS-Bridge/custom bridge — https://www.pressian.com/
- **South Korea — Sejong Institute** — RSSHub if a maintained route exists; otherwise RSS-Bridge/custom bridge — https://www.sejong.org/
- **South Korea — The Korea Herald** — RSSHub if a maintained route exists; otherwise RSS-Bridge/custom bridge — https://www.koreaherald.com/
- **South Korea — The Korea Times** — RSSHub if a maintained route exists; otherwise RSS-Bridge/custom bridge — https://www.koreatimes.co.kr/
- **South Korea — Yonhap News Agency (연합뉴스)** — RSSHub if a maintained route exists; otherwise RSS-Bridge/custom bridge — https://www.yna.co.kr/
- **South Korea — ZDNet Korea** — RSSHub if a maintained route exists; otherwise RSS-Bridge/custom bridge — https://zdnet.co.kr/
- **Taiwan — China Times (中國時報)** — RSSHub if a maintained route exists; otherwise RSS-Bridge/custom bridge — https://www.chinatimes.com/
- **Taiwan — CommonWealth Magazine (天下雜誌)** — RSSHub if a maintained route exists; otherwise RSS-Bridge/custom bridge — https://www.cw.com.tw/
- **Taiwan — DigiTimes** — RSSHub if a maintained route exists; otherwise RSS-Bridge/custom bridge — https://www.digitimes.com/
- **Taiwan — Doublethink Lab** — RSSHub if a maintained route exists; otherwise RSS-Bridge/custom bridge — https://doublethinklab.org/
- **Taiwan — Inside** — RSSHub if a maintained route exists; otherwise RSS-Bridge/custom bridge — https://www.inside.com.tw/
- **Taiwan — Mirror Media (鏡週刊 / 鏡新聞)** — RSSHub if a maintained route exists; otherwise RSS-Bridge/custom bridge — https://www.mirrormedia.mg/
- **Taiwan — Prospect Foundation** — RSSHub if a maintained route exists; otherwise RSS-Bridge/custom bridge — https://www.pf.org.tw/
- **Taiwan — Storm Media (風傳媒)** — RSSHub if a maintained route exists; otherwise RSS-Bridge/custom bridge — https://www.storm.mg/
- **Taiwan — Taiwan FactCheck Center** — RSSHub if a maintained route exists; otherwise RSS-Bridge/custom bridge — https://tfc-taiwan.org.tw/
- **Taiwan — Taiwan News** — RSSHub if a maintained route exists; otherwise RSS-Bridge/custom bridge — https://www.taiwannews.com.tw/
- **Taiwan — Taiwan-Asia Exchange Foundation** — RSSHub if a maintained route exists; otherwise RSS-Bridge/custom bridge — https://www.taef.org/
- **Taiwan — The Reporter (報導者)** — RSSHub if a maintained route exists; otherwise RSS-Bridge/custom bridge — https://www.twreporter.org/
- **Taiwan — United Daily News (聯合新聞網 / UDN)** — RSSHub if a maintained route exists; otherwise RSS-Bridge/custom bridge — https://udn.com/
- **Taiwan — iThome** — RSSHub if a maintained route exists; otherwise RSS-Bridge/custom bridge — https://www.ithome.com.tw/
- **United States — Asia Maritime Transparency Initiative (CSIS)** — RSSHub if a maintained route exists; otherwise RSS-Bridge/custom bridge — https://amti.csis.org/
- **United States — Associated Press (AP)** — RSSHub if a maintained route exists; otherwise RSS-Bridge/custom bridge — https://apnews.com/
- **United States — Axios** — RSSHub if a maintained route exists; otherwise RSS-Bridge/custom bridge — https://www.axios.com/
- **United States — Beyond Parallel (CSIS)** — RSSHub if a maintained route exists; otherwise RSS-Bridge/custom bridge — https://beyondparallel.csis.org/
- **United States — Bloomberg** — RSSHub if a maintained route exists; otherwise RSS-Bridge/custom bridge — https://www.bloomberg.com/
- **United States — Carnegie Endowment** — RSSHub if a maintained route exists; otherwise RSS-Bridge/custom bridge — https://carnegieendowment.org/
- **United States — Center for a New American Security** — RSSHub if a maintained route exists; otherwise RSS-Bridge/custom bridge — https://www.cnas.org/
- **United States — ChinaPower Project (CSIS)** — RSSHub if a maintained route exists; otherwise RSS-Bridge/custom bridge — https://chinapower.csis.org/
- **United States — Defense One** — RSSHub if a maintained route exists; otherwise RSS-Bridge/custom bridge — https://www.defenseone.com/
- **United States — Foreign Affairs** — RSSHub if a maintained route exists; otherwise RSS-Bridge/custom bridge — https://www.foreignaffairs.com/
- **United States — Foreign Policy** — RSSHub if a maintained route exists; otherwise RSS-Bridge/custom bridge — https://foreignpolicy.com/
- **United States — Reuters U.S.** — RSSHub if a maintained route exists; otherwise RSS-Bridge/custom bridge — https://www.reuters.com/world/us/
- **United States — Semafor** — RSSHub if a maintained route exists; otherwise RSS-Bridge/custom bridge — https://www.semafor.com/
- **United States — The Atlantic** — RSSHub if a maintained route exists; otherwise RSS-Bridge/custom bridge — https://www.theatlantic.com/
- **United States — The Wall Street Journal** — RSSHub if a maintained route exists; otherwise RSS-Bridge/custom bridge — https://www.wsj.com/
- **United States — USA Today** — RSSHub if a maintained route exists; otherwise RSS-Bridge/custom bridge — https://www.usatoday.com/

# Sources Requiring Direct Scraping or Playwright

- **Direct scraping — China — Anquanke (安全客)** — https://www.anquanke.com/ — Community/vendor content mix.
- **Direct scraping — China — Caijing (财经)** — https://www.caijing.com.cn/ — Some premium content.
- **Direct scraping — China — Caixin (财新)** — https://www.caixin.com/ — Strong paywall; subscription/session needed.
- **Direct scraping — China — Center for China and Globalization (CCG)** — http://en.ccg.org.cn/ — Low-volume, report/event-heavy; some sites have inconsistent accessibility.
- **Direct scraping — China — China News Service (中国新闻网)** — https://www.chinanews.com.cn/ — Standard article/listing extraction.
- **Direct scraping — China — Economic Daily (经济日报)** — http://www.ce.cn/ — Legacy site.
- **Direct scraping — China — FreeBuf** — https://www.freebuf.com/ — Community content quality varies.
- **Direct scraping — China — Global Times (环球时报)** — https://www.globaltimes.cn/ — Distinguish rhetoric/commentary from formal policy.
- **Direct scraping — China — GreatFire.org** — https://en.greatfire.org/ — Technical data may need custom parser.
- **Direct scraping — China — LatePost (晚点)** — https://www.latepost.com/ — Some subscription/app-first content.
- **Direct scraping — China — PLA Daily / China Military Online (解放军报/中国军网)** — http://www.81.cn/ — Archive snapshots; content/site can change.
- **Direct scraping — China — People's Daily (人民日报)** — http://www.people.com.cn/ — Legacy structures; versioning important for edits/deletions.
- **Direct scraping — China — Shanghai Institutes for International Studies (SIIS)** — https://www.siis.org.cn/ — Low-volume, report/event-heavy; some sites have inconsistent accessibility.
- **Direct scraping — China — Southern Weekly (南方周末)** — https://www.infzm.com/ — Censorship constraints; paywall may apply.
- **Direct scraping — China — TMTPost (钛媒体)** — https://www.tmtpost.com/ — Some premium content.
- **Direct scraping — China — The Beijing News (新京报)** — https://www.bjnews.com.cn/ — Standard article/listing extraction.
- **Direct scraping — China — Yicai / First Financial (第一财经)** — https://www.yicai.com/ — Dynamic pages.
- **Direct scraping — Indo-Pacific / Regional — Asia Society Policy Institute** — https://asiasociety.org/policy-institute — No broad RSS verified.
- **Direct scraping — Indo-Pacific / Regional — BenarNews** — https://www.benarnews.org/ — Blocked in some countries; feed structures vary.
- **Direct scraping — Indo-Pacific / Regional — East-West Center** — https://www.eastwestcenter.org/ — No broad RSS verified.
- **Direct scraping — Indo-Pacific / Regional — ISEAS – Yusof Ishak Institute** — https://www.iseas.edu.sg/ — Some publications/paywall.
- **Direct scraping — Indo-Pacific / Regional — International Institute for Strategic Studies (IISS)** — https://www.iiss.org/ — Premium reports/products.
- **Direct scraping — Indo-Pacific / Regional — Janes** — https://www.janes.com/ — Hard paywall/licensing; subscription integration preferable.
- **Direct scraping — Indo-Pacific / Regional — Pacific Forum** — https://pacforum.org/ — No broad RSS verified.
- **Direct scraping — Indo-Pacific / Regional — RSIS** — https://www.rsis.edu.sg/ — No broad RSS verified.
- **Direct scraping — Indo-Pacific / Regional — South China Morning Post** — https://www.scmp.com/ — Paywall/anti-bot; licensed access may be preferable.
- **Direct scraping — Indo-Pacific / Regional — The Straits Times** — https://www.straitstimes.com/ — Paywall on many stories.
- **Direct scraping — Japan — Bunshun Online (文春オンライン)** — https://bunshun.jp/ — Paywall/member content; tabloid mix.
- **Direct scraping — Japan — Chunichi Shimbun (中日新聞)** — https://www.chunichi.co.jp/ — Standard article/listing extraction.
- **Direct scraping — Japan — Diamond Online (ダイヤモンド・オンライン)** — https://diamond.jp/ — Paywall/premium content.
- **Direct scraping — Japan — Hokkaido Shimbun (北海道新聞)** — https://www.hokkaido-np.co.jp/ — Paywall possible.
- **Direct scraping — Japan — IDE-JETRO** — https://www.ide.go.jp/English/ — PDF-heavy or low-frequency institutional publishing.
- **Direct scraping — Japan — ITmedia** — https://www.itmedia.co.jp/ — Multiple subsites.
- **Direct scraping — Japan — Institute of Geoeconomics (IOG)** — https://instituteofgeoeconomics.org/ — PDF-heavy or low-frequency institutional publishing.
- **Direct scraping — Japan — JBpress** — https://jbpress.ismedia.jp/ — Opinion-heavy; some member content.
- **Direct scraping — Japan — Japan Institute of International Affairs (JIIA)** — https://www.jiia.or.jp/ — PDF-heavy or low-frequency institutional publishing.
- **Direct scraping — Japan — Jiji Press (時事通信)** — https://www.jiji.com/ — Standard article/listing extraction.
- **Direct scraping — Japan — Kahoku Shimpo (河北新報)** — https://kahoku.news/ — Standard article/listing extraction.
- **Direct scraping — Japan — Kobe Shimbun (神戸新聞)** — https://www.kobe-np.co.jp/ — Standard article/listing extraction.
- **Direct scraping — Japan — Kyodo News (共同通信)** — https://www.kyodo.co.jp/ — Public full-text limited; licensing may be preferable.
- **Direct scraping — Japan — Mainichi Shimbun (毎日新聞)** — https://mainichi.jp/ — Metered/paywalled.
- **Direct scraping — Japan — NHK News Web** — https://www3.nhk.or.jp/news/ — Dynamic pages; no broad RSS verified; respect terms.
- **Direct scraping — Japan — Nikkei (日本経済新聞)** — https://www.nikkei.com/ — Strong paywall; licensed access preferable.
- **Direct scraping — Japan — Nikkei Asia** — https://asia.nikkei.com/ — Paywall.
- **Direct scraping — Japan — Nishinippon Shimbun (西日本新聞)** — https://www.nishinippon.co.jp/ — Paywall on some content.
- **Direct scraping — Japan — Sasakawa Peace Foundation** — https://www.spf.org/ — PDF-heavy or low-frequency institutional publishing.
- **Direct scraping — Japan — ScanNetSecurity** — https://scan.netsecurity.ne.jp/ — Some member content.
- **Direct scraping — Japan — Security NEXT** — https://www.security-next.com/ — Standard article/listing extraction.
- **Direct scraping — Japan — Tansa** — https://tansajp.org/ — Low volume, deep investigations.
- **Direct scraping — Japan — Tokyo Shimbun (東京新聞)** — https://www.tokyo-np.co.jp/ — Some paywall.
- **Direct scraping — Japan — Toyo Keizai Online (東洋経済オンライン)** — https://toyokeizai.net/ — Some premium content.
- **Direct scraping — Japan — Yomiuri Shimbun (読売新聞)** — https://www.yomiuri.co.jp/ — Paywall/membership on some content.
- **Direct scraping — North Korea / DPRK Monitoring — CSIS Beyond Parallel** — https://beyondparallel.csis.org/ — Image-heavy; archive imagery metadata.
- **Direct scraping — North Korea / DPRK Monitoring — Committee for Human Rights in North Korea (HRNK)** — https://www.hrnk.org/ — Reports/PDFs; advocacy perspective.
- **Direct scraping — North Korea / DPRK Monitoring — KINU DPRK Research** — https://www.kinu.or.kr/ — PDF-heavy.
- **Direct scraping — North Korea / DPRK Monitoring — Korea Risk Group** — https://www.korearisk.com/ — Subscription/commercial access.
- **Direct scraping — North Korea / DPRK Monitoring — Korean Central News Agency (KCNA)** — http://www.kcna.kp/ — Intermittent accessibility, DNS/TLS/geoblocking; retries/snapshots needed.
- **Direct scraping — North Korea / DPRK Monitoring — NK News** — https://www.nknews.org/ — Strong paywall; subscription/session handling required.
- **Direct scraping — North Korea / DPRK Monitoring — NK Pro** — https://www.nknews.org/pro/ — Hard paywall/subscription and licensing constraints.
- **Direct scraping — North Korea / DPRK Monitoring — Naenara** — http://www.naenara.com.kp/ — Connectivity can be unstable; legacy HTML.
- **Direct scraping — North Korea / DPRK Monitoring — Rodong Sinmun (로동신문)** — http://www.rodong.rep.kp/ — Intermittent .kp accessibility; archive every version.
- **Direct scraping — North Korea / DPRK Monitoring — Voice of Korea** — http://www.vok.rep.kp/ — Audio/media extraction and intermittent access.
- **Direct scraping — Philippines — Daily Tribune** — https://tribune.net.ph/ — No broad RSS verified.
- **Direct scraping — Philippines — Manila Bulletin** — https://mb.com.ph/ — No broad RSS verified.
- **Direct scraping — Philippines — Philippine News Agency (PNA)** — https://www.pna.gov.ph/ — Government perspective; no broad RSS verified.
- **Direct scraping — Philippines — Stratbase ADR Institute** — https://adrinstitute.org/ — Low-frequency research/event pages; verify publication URLs during onboarding.
- **Direct scraping — Philippines — SunStar** — https://www.sunstar.com.ph/ — Multiple city editions; no broad RSS verified.
- **Direct scraping — Philippines — The Manila Times** — https://www.manilatimes.net/ — Paywall/subscription on some content.
- **Direct scraping — Philippines — The Philippine Star / Philstar.com** — https://www.philstar.com/ — No broad RSS verified.
- **Direct scraping — South Korea — Boannews (보안뉴스)** — https://www.boannews.com/ — Standard article/listing extraction.
- **Direct scraping — South Korea — Chosun Ilbo (조선일보)** — https://www.chosun.com/ — Some paywall/anti-bot; multilingual editions.
- **Direct scraping — South Korea — Dailyan (데일리안)** — https://www.dailian.co.kr/ — Standard article/listing extraction.
- **Direct scraping — South Korea — Dong-A Ilbo (동아일보)** — https://www.donga.com/ — RSS link visible; exact endpoint discovery needed; reuse restrictions.
- **Direct scraping — South Korea — East Asia Institute (EAI)** — https://www.eai.or.kr/ — Standard article/listing extraction.
- **Direct scraping — South Korea — Hankyoreh (한겨레)** — https://www.hani.co.kr/ — Robots/site access can complicate scraping.
- **Direct scraping — South Korea — Institute for National Security Strategy (INSS)** — https://www.inss.re.kr/ — PDF-heavy; extract publications and metadata.
- **Direct scraping — South Korea — Korea Economic Daily (한국경제)** — https://www.hankyung.com/ — Some subscription products.
- **Direct scraping — South Korea — Korea Institute for Defense Analyses (KIDA)** — https://www.kida.re.kr/ — PDF-heavy; extract publications and metadata.
- **Direct scraping — South Korea — Korea Institute for International Economic Policy (KIEP)** — https://www.kiep.go.kr/ — PDF-heavy; extract publications and metadata.
- **Direct scraping — South Korea — Korea Institute for National Unification (KINU)** — https://www.kinu.or.kr/ — PDF-heavy; extract publications and metadata.
- **Direct scraping — South Korea — Korea Policy Briefing (정책브리핑)** — https://www.korea.kr/ — RSS service discontinued 2026-07-01; replace with scraping/change monitoring.
- **Direct scraping — South Korea — New Daily (뉴데일리)** — https://www.newdaily.co.kr/ — Opinion-heavy.
- **Direct scraping — South Korea — News1 Korea (뉴스1)** — https://www.news1.kr/ — Robots/access restrictions may require browser/licensed access.
- **Direct scraping — South Korea — Pressian (프레시안)** — https://www.pressian.com/ — Standard article/listing extraction.
- **Direct scraping — South Korea — Sejong Institute** — https://www.sejong.org/ — Standard article/listing extraction.
- **Direct scraping — South Korea — Seoul National University Institute for Peace and Unification Studies** — https://ipus.snu.ac.kr/ — Standard article/listing extraction.
- **Direct scraping — South Korea — SisaIN (시사IN)** — https://www.sisain.co.kr/ — Some subscriber content.
- **Direct scraping — South Korea — The Korea Herald** — https://www.koreaherald.com/ — Standard article/listing extraction.
- **Direct scraping — South Korea — The Korea Times** — https://www.koreatimes.co.kr/ — Standard article/listing extraction.
- **Direct scraping — South Korea — Yonhap News Agency (연합뉴스)** — https://www.yna.co.kr/ — Robots/anti-bot restrictions; licensed/API access may be preferable.
- **Direct scraping — South Korea — ZDNet Korea** — https://zdnet.co.kr/ — Standard article/listing extraction.
- **Direct scraping — Taiwan — Academia Sinica** — https://www.sinica.edu.tw/en — Standard article/listing extraction.
- **Direct scraping — Taiwan — China Times (中國時報)** — https://www.chinatimes.com/ — Dynamic site.
- **Direct scraping — Taiwan — CommonWealth Magazine (天下雜誌)** — https://www.cw.com.tw/ — Premium paywall.
- **Direct scraping — Taiwan — DigiTimes** — https://www.digitimes.com/ — Subscription/paywall; licensed access may be needed.
- **Direct scraping — Taiwan — Doublethink Lab** — https://doublethinklab.org/ — Standard article/listing extraction.
- **Direct scraping — Taiwan — Inside** — https://www.inside.com.tw/ — No broad RSS verified.
- **Direct scraping — Taiwan — Institute for National Defense and Security Research (INDSR)** — https://indsr.org.tw/ — Reports/PDFs; low-volume institutional output.
- **Direct scraping — Taiwan — Mirror Media (鏡週刊 / 鏡新聞)** — https://www.mirrormedia.mg/ — Some tabloid/lifestyle mix.
- **Direct scraping — Taiwan — Prospect Foundation** — https://www.pf.org.tw/ — Standard article/listing extraction.
- **Direct scraping — Taiwan — Storm Media (風傳媒)** — https://www.storm.mg/ — Mix reporting/opinion.
- **Direct scraping — Taiwan — Taiwan FactCheck Center** — https://tfc-taiwan.org.tw/ — Standard article/listing extraction.
- **Direct scraping — Taiwan — Taiwan News** — https://www.taiwannews.com.tw/ — Site structure changes periodically.
- **Direct scraping — Taiwan — Taiwan-Asia Exchange Foundation** — https://www.taef.org/ — Standard article/listing extraction.
- **Direct scraping — Taiwan — The Reporter (報導者)** — https://www.twreporter.org/ — Low volume/high value; preserve multimedia/data.
- **Direct scraping — Taiwan — United Daily News (聯合新聞網 / UDN)** — https://udn.com/ — Dynamic pages/ads.
- **Direct scraping — Taiwan — iThome** — https://www.ithome.com.tw/ — Standard article/listing extraction.
- **Direct scraping — United States — Asia Maritime Transparency Initiative (CSIS)** — https://amti.csis.org/ — Standard article/listing extraction.
- **Direct scraping — United States — Associated Press (AP)** — https://apnews.com/ — Public feeds limited; licensing terms matter for full-text reuse.
- **Direct scraping — United States — Axios** — https://www.axios.com/ — Newsletter-heavy; no broad RSS verified.
- **Direct scraping — United States — Beyond Parallel (CSIS)** — https://beyondparallel.csis.org/ — Standard article/listing extraction.
- **Direct scraping — United States — Bloomberg** — https://www.bloomberg.com/ — Strong paywall/anti-bot; licensed/API access preferable.
- **Direct scraping — United States — Carnegie Endowment** — https://carnegieendowment.org/ — Standard article/listing extraction.
- **Direct scraping — United States — Center for a New American Security** — https://www.cnas.org/ — Standard article/listing extraction.
- **Direct scraping — United States — ChinaPower Project (CSIS)** — https://chinapower.csis.org/ — Standard article/listing extraction.
- **Direct scraping — United States — Defense One** — https://www.defenseone.com/ — Standard article/listing extraction.
- **Direct scraping — United States — Foreign Affairs** — https://www.foreignaffairs.com/ — Paywall/subscription may apply.
- **Direct scraping — United States — Foreign Policy** — https://foreignpolicy.com/ — Paywall/subscription may apply.
- **Direct scraping — United States — RealClearPolitics** — https://www.realclearpolitics.com/ — Standard article/listing extraction.
- **Direct scraping — United States — Reuters U.S.** — https://www.reuters.com/world/us/ — Public RSS limited; licensing/redistribution restrictions; licensed/API access preferable.
- **Direct scraping — United States — Semafor** — https://www.semafor.com/ — Standard article/listing extraction.
- **Direct scraping — United States — Stanford APARC** — https://aparc.fsi.stanford.edu/ — Standard article/listing extraction.
- **Direct scraping — United States — The Atlantic** — https://www.theatlantic.com/ — Some subscription/paywall or membership content may apply.
- **Direct scraping — United States — The Daily Wire** — https://www.dailywire.com/ — Some subscription/paywall or membership content may apply.
- **Direct scraping — United States — The Wall Street Journal** — https://www.wsj.com/ — Hard paywall/anti-bot; licensed access preferable.
- **Direct scraping — United States — U.S. Space Force** — https://www.spaceforce.mil/ — Standard article/listing extraction.
- **Direct scraping — United States — USA Today** — https://www.usatoday.com/ — Standard article/listing extraction.
- **Direct scraping — United States — Washington Examiner** — https://www.washingtonexaminer.com/ — Standard article/listing extraction.
- **Playwright — China — 36Kr (36氪)** — https://36kr.com/ — JS-heavy/app-centric; anti-bot possible.
- **Playwright — China — Huxiu (虎嗅)** — https://www.huxiu.com/ — Membership content; JS-heavy.
- **Playwright — China — Jiemian News (界面新闻)** — https://www.jiemian.com/ — JS-heavy.
- **Playwright — China — The Paper (澎湃新闻)** — https://www.thepaper.cn/ — JavaScript-heavy/anti-bot.
- **Playwright — Japan — Asahi Shimbun (朝日新聞)** — https://www.asahi.com/ — Paywall and robots/anti-bot.
- **Playwright — Japan — Okinawa Times (沖縄タイムス)** — https://www.okinawatimes.co.jp/ — Robots/access restrictions and paywalled items.
- **Playwright — Japan — Sankei Shimbun (産経新聞)** — https://www.sankei.com/ — Robots/access limits.
- **Playwright — Philippines — Commission on Elections (COMELEC)** — https://comelec.gov.ph/ — Automated access can be unreliable.
- **Playwright — Philippines — Office of the President of the Philippines** — https://president.gov.ph/ — Automated access may return 403/WAF.
- **Playwright — Philippines — Official Gazette of the Republic of the Philippines** — https://www.officialgazette.gov.ph/ — Automated access can be blocked/403.
- **Playwright — Philippines — Senate of the Philippines** — https://legacy.senate.gov.ph/ — Legacy site/automated access restrictions.
- **Playwright — South Korea — JoongAng Ilbo (중앙일보)** — https://www.joongang.co.kr/ — Robots/anti-bot restrictions observed.

# Government Pages Best Suited for changedetection.io

These pages are generally low-to-medium volume, high-value primary sources where a release/index change can trigger downstream scraping and document-version capture.

- **China — China Coast Guard (中国海警局)** — https://www.ccg.gov.cn/ — Maritime enforcement; East/South China Sea; patrols
- **China — China Institute of International Studies (CIIS)** — https://www.ciis.org.cn/ — Foreign policy; U.S.-China; Taiwan; security; economy
- **China — China Institutes of Contemporary International Relations (CICIR)** — http://www.cicir.ac.cn/ — Foreign policy; U.S.-China; Taiwan; security; economy
- **China — Chinese Academy of Social Sciences (CASS)** — http://www.cass.cn/ — Foreign policy; U.S.-China; Taiwan; security; economy
- **China — Cyberspace Administration of China (国家互联网信息办公室)** — https://www.cac.gov.cn/ — Internet regulation; censorship; data; AI rules
- **China — Ministry of Commerce (商务部)** — http://www.mofcom.gov.cn/ — Trade; export controls; sanctions; foreign investment
- **China — Ministry of Foreign Affairs (外交部)** — https://www.mfa.gov.cn/ — Diplomacy; spokesperson briefings; sanctions; Taiwan
- **China — Ministry of National Defense (国防部)** — http://www.mod.gov.cn/ — PLA; defense policy; press briefings; exercises
- **China — Ministry of Public Security (公安部)** — https://www.mps.gov.cn/ — Police; crime; border/security; campaigns
- **China — National Development and Reform Commission (国家发展改革委)** — https://www.ndrc.gov.cn/ — Industrial policy; energy; prices; economic planning
- **China — National People's Congress (全国人大)** — http://www.npc.gov.cn/ — Laws; legislation; sessions; committee decisions
- **China — People's Bank of China (中国人民银行)** — http://www.pbc.gov.cn/ — Monetary policy; financial regulation; data
- **China — State Administration for Market Regulation** — https://www.samr.gov.cn/ — Antitrust; market regulation; corporate enforcement
- **China — State Council of the PRC (中国政府网)** — https://www.gov.cn/ — State Council; regulations; policy; leadership
- **China — Supreme People's Court (最高人民法院)** — https://www.court.gov.cn/ — Judicial interpretations; major cases; court policy
- **China — Supreme People's Procuratorate (最高人民检察院)** — https://www.spp.gov.cn/ — Prosecutions; anti-corruption; major cases
- **China — Taiwan Affairs Office of the State Council (国台办)** — https://www.gwytb.gov.cn/ — Taiwan; cross-strait; press conferences; policy
- **Indo-Pacific / Regional — APEC** — https://www.apec.org/ — Trade; economic policy; leaders' meetings
- **Indo-Pacific / Regional — ASEAN** — https://asean.org/ — Southeast Asia diplomacy; security; summits
- **Indo-Pacific / Regional — American Institute in Taiwan (AIT)** — https://www.ait.org.tw/ — U.S.-Taiwan relations; security; visits
- **Indo-Pacific / Regional — Asia/Pacific Group on Money Laundering (APG)** — https://apgml.org/ — AML/CFT; mutual evaluations; sanctions implementation
- **Indo-Pacific / Regional — Embassy of Japan in the United States** — https://www.us.emb-japan.go.jp/itprtop_en/index.html — Japan-U.S. diplomacy; security
- **Indo-Pacific / Regional — Embassy of the Republic of Korea in the U.S.** — https://overseas.mofa.go.kr/us-en/index.do — Korea-U.S. diplomacy; policy
- **Indo-Pacific / Regional — Financial Action Task Force (FATF)** — https://www.fatf-gafi.org/ — AML/CFT; sanctions; country evaluations
- **Indo-Pacific / Regional — IMF Asia and Pacific** — https://www.imf.org/en/Regions/Asia-and-Pacific — Macroeconomy; country surveillance; regional outlook
- **Indo-Pacific / Regional — Taipei Economic and Cultural Representative Office in the U.S. (TECRO)** — https://www.roc-taiwan.org/us_en/index.html — Taiwan-U.S. diplomacy; security; statements
- **Indo-Pacific / Regional — U.S. Embassy Beijing** — https://china.usembassy-china.org.cn/ — U.S.-China relations; statements
- **Indo-Pacific / Regional — U.S. Embassy Manila** — https://ph.usembassy.gov/ — U.S.-Philippines alliance; WPS; exercises
- **Indo-Pacific / Regional — U.S. Embassy Seoul** — https://kr.usembassy.gov/ — U.S.-Korea relations; statements
- **Indo-Pacific / Regional — U.S. Embassy Tokyo** — https://jp.usembassy.gov/ — U.S.-Japan alliance; diplomacy; security
- **Indo-Pacific / Regional — UN ESCAP** — https://www.unescap.org/ — Asia-Pacific economy; development; data
- **Indo-Pacific / Regional — UN Security Council** — https://main.un.org/securitycouncil/ — Sanctions; resolutions; DPRK; international security
- **Indo-Pacific / Regional — WHO Western Pacific** — https://www.who.int/westernpacific — Health emergencies; regional public health
- **Indo-Pacific / Regional — World Bank East Asia & Pacific** — https://www.worldbank.org/en/region/eap — Economy; development; country data
- **Japan — Acquisition, Technology & Logistics Agency (ATLA)** — https://www.mod.go.jp/atla/ — Defense procurement; R&D; acquisition
- **Japan — Cabinet Secretariat (内閣官房)** — https://www.cas.go.jp/ — National security; cabinet decisions; crisis response
- **Japan — House of Councillors (参議院)** — https://www.sangiin.go.jp/ — Bills; committees; plenary; records
- **Japan — House of Representatives (衆議院)** — https://www.shugiin.go.jp/ — Bills; committees; plenary; records
- **Japan — Japan Coast Guard (海上保安庁)** — https://www.kaiho.mlit.go.jp/ — Maritime incidents; Senkaku; navigation; rescues
- **Japan — Ministry of Foreign Affairs of Japan (MOFA)** — https://www.mofa.go.jp/ — Diplomacy; treaties; sanctions; statements
- **Japan — Ministry of Internal Affairs and Communications (MIC)** — https://www.soumu.go.jp/ — Elections; telecom; local government; statistics
- **Japan — National Institute for Defense Studies (NIDS)** — https://www.nids.mod.go.jp/ — Foreign policy; defense; China; Korea; economic security; Indo-Pacific
- **Japan — Public Security Intelligence Agency (公安調査庁)** — https://www.moj.go.jp/psia/ — Security threats; economic security; extremism
- **Japan — Supreme Court of Japan / Courts** — https://www.courts.go.jp/ — Judgments; court administration; case information
- **North Korea / DPRK Monitoring — DPRK Ministry of Foreign Affairs** — http://www.mfa.gov.kp/ — Diplomacy; statements; U.S.; sanctions
- **North Korea / DPRK Monitoring — International Atomic Energy Agency (IAEA) - DPRK** — https://www.iaea.org/topics/dprk — Nuclear program; safeguards; satellite observations
- **North Korea / DPRK Monitoring — North Korea Information Portal (Unification Ministry)** — https://nkinfo.unikorea.go.kr/ — DPRK data; leadership; institutions; statistics
- **North Korea / DPRK Monitoring — UN Human Rights Office - DPRK** — https://seoul.ohchr.org/en — DPRK human rights; investigations; reports
- **North Korea / DPRK Monitoring — UN Security Council DPRK Sanctions Committee (1718)** — https://main.un.org/securitycouncil/en/sanctions/1718 — Sanctions; designated entities; implementation notices
- **Philippines — Armed Forces of the Philippines (AFP)** — https://www.afp.mil.ph/ — Military operations; West Philippine Sea; exercises
- **Philippines — Department of Foreign Affairs (DFA)** — https://dfa.gov.ph/ — Diplomacy; China; treaties; consular; statements
- **Philippines — Department of National Defense (DND)** — https://www.dnd.gov.ph/ — Defense policy; acquisitions; security
- **Philippines — House of Representatives of the Philippines** — https://www.congress.gov.ph/ — Bills; committees; press releases; hearings
- **Philippines — National Intelligence Coordinating Agency (NICA)** — https://nica.gov.ph/ — Public intelligence notices; national security
- **Philippines — National Security Council of the Philippines** — https://nsc.gov.ph/ — National security; WPS; insurgency; policy
- **Philippines — Philippine Air Force** — https://www.paf.mil.ph/ — Air operations; exercises; procurement
- **Philippines — Philippine Army** — https://army.mil.ph/ — Army operations; insurgency; exercises
- **Philippines — Philippine Coast Guard** — https://coastguard.gov.ph/ — West Philippine Sea; maritime incidents; rescues
- **Philippines — Philippine National Police (PNP)** — https://pnp.gov.ph/ — Crime; investigations; public safety
- **Philippines — Philippine Navy** — https://www.navy.mil.ph/ — Naval operations; WPS; exercises
- **Philippines — Presidential Communications Office (PCO)** — https://pco.gov.ph/ — Palace briefings; speeches; press releases
- **Philippines — Supreme Court of the Philippines** — https://sc.judiciary.gov.ph/ — Decisions; resolutions; current cases; announcements
- **South Korea — Constitutional Court of Korea (헌법재판소)** — https://www.ccourt.go.kr/ — Constitutional decisions; hearings; press releases
- **South Korea — Korea Communications Commission** — https://www.kcc.go.kr/ — Media regulation; platforms; broadcasting
- **South Korea — Korean National Police Agency (경찰청)** — https://www.police.go.kr/ — Crime; investigations; public safety
- **South Korea — Ministry of Foreign Affairs (외교부)** — https://www.mofa.go.kr/ — Diplomacy; sanctions; treaties; briefings
- **South Korea — Ministry of National Defense (국방부)** — https://www.mnd.go.kr/ — Defense policy; military operations; exercises
- **South Korea — Ministry of Unification (통일부)** — https://www.unikorea.go.kr/ — North Korea; inter-Korean relations; defectors
- **South Korea — National Assembly (대한민국 국회)** — https://www.assembly.go.kr/ — Bills; committees; plenary sessions; press releases
- **South Korea — National Intelligence Service (국가정보원)** — https://www.nis.go.kr/ — Counterintelligence; cyber; North Korea; public notices
- **South Korea — Office of the President (대통령실)** — https://www.president.go.kr/ — Presidential speeches; briefings; appointments; policy
- **South Korea — ROK Joint Chiefs of Staff (합동참모본부)** — https://www.jcs.mil.kr/ — North Korea activity; exercises; operational statements
- **South Korea — Republic of Korea Air Force** — https://www.airforce.mil.kr/ — Air operations; exercises; procurement
- **South Korea — Republic of Korea Army** — https://www.army.mil.kr/ — Army operations; exercises; personnel
- **South Korea — Republic of Korea Navy** — https://www.navy.mil.kr/ — Naval operations; exercises; ship activity
- **South Korea — Supreme Court of Korea (대한민국 법원)** — https://www.scourt.go.kr/ — Judgments; court news; administration
- **Taiwan — Administration for Cyber Security, MODA** — https://moda.gov.tw/ACS/ — Cybersecurity; incidents; policy; resilience
- **Taiwan — Central Election Commission (中央選舉委員會)** — https://www.cec.gov.tw/ — Elections; referendums; regulations; results
- **Taiwan — Coast Guard Administration (海巡署)** — https://www.cga.gov.tw/ — Maritime incidents; gray-zone activity; patrols
- **Taiwan — Constitutional Court (憲法法庭)** — https://cons.judicial.gov.tw/ — Constitutional judgments; hearings; petitions
- **Taiwan — Executive Yuan (行政院)** — https://www.ey.gov.tw/ — Cabinet policy; press releases; regulations
- **Taiwan — Judicial Yuan (司法院)** — https://www.judicial.gov.tw/ — Court administration; judgments; judicial news
- **Taiwan — Legislative Yuan (立法院)** — https://www.ly.gov.tw/ — Bills; committees; hearings; parliamentary news
- **Taiwan — Ministry of National Defense (國防部)** — https://www.mnd.gov.tw/ — PLA activity; defense policy; exercises; procurement
- **Taiwan — National Chung-Shan Institute of Science and Technology (NCSIST)** — https://www.ncsist.org.tw/ — Defense technology; missiles; drones; R&D
- **Taiwan — National Police Agency (警政署)** — https://www.npa.gov.tw/ — Crime; public safety; cybercrime
- **Taiwan — National Security Bureau (國家安全局)** — https://www.nsb.gov.tw/ — National security; intelligence; public reports
- **United States — Central Intelligence Agency** — https://www.cia.gov/ — Intelligence; statements; declassified material
- **United States — National Security Agency** — https://www.nsa.gov/ — Cybersecurity; cryptography; intelligence; advisories
- **United States — Office of the Director of National Intelligence** — https://www.dni.gov/ — Threat assessments; intelligence community statements
- **United States — Supreme Court of the United States** — https://www.supremecourt.gov/ — Opinions; orders; oral arguments; docket
- **United States — U.S. Courts** — https://www.uscourts.gov/ — Court administration; rules; federal court news
- **United States — U.S. Department of State** — https://www.state.gov/ — Diplomacy; sanctions; treaties; press briefings
- **United States — U.S. House of Representatives** — https://www.house.gov/ — House floor; committees; leadership
- **United States — U.S. Indo-Pacific Command** — https://www.pacom.mil/ — Indo-Pacific operations; exercises; posture
- **United States — U.S. Senate** — https://www.senate.gov/ — Senate floor; committees; nominations
- **United States — White House** — https://www.whitehouse.gov/ — Presidential actions; speeches; fact sheets; briefings

# YouTube Channels to Monitor with yt-dlp

Production should resolve each mutable `@handle` to an immutable YouTube `channel_id`, use the native channel Atom feed for new-video discovery where possible, and invoke yt-dlp only for metadata/subtitles/media. Channels without a verified URL in the inventory require channel-ID discovery before activation.

- **China — CCTV News / 央视新闻** — https://www.youtube.com/@CCTVVideoNewsAgency
- **China — CGTN** — https://www.youtube.com/@cgtn
- **China — China Daily** — https://www.youtube.com/@chinadaily
- **China — Global Times (环球时报)** — https://www.youtube.com/@globaltimes
- **China — Xinhua News Agency (新华社)** — https://www.youtube.com/@NewChinaTV
- **Indo-Pacific / Regional — Channel News Asia (Singapore)** — https://www.youtube.com/@channelnewsasia
- **Indo-Pacific / Regional — International Institute for Strategic Studies (IISS)** — https://www.youtube.com/@IISSorg
- **Indo-Pacific / Regional — Naval News** — https://www.youtube.com/@NavalNews
- **Indo-Pacific / Regional — Radio Free Asia** — https://www.youtube.com/@RFAVideo
- **Indo-Pacific / Regional — Voice of America** — https://www.youtube.com/@VOANews
- **Japan — Japan Air Self-Defense Force (航空自衛隊)** — https://www.youtube.com/@JASDFchannel
- **Japan — Japan Ground Self-Defense Force (陸上自衛隊)** — https://www.youtube.com/@JGSDFchannel
- **Japan — Japan Joint Staff (統合幕僚監部)** — https://www.youtube.com/@jointstaffjapan
- **Japan — Japan Maritime Self-Defense Force (海上自衛隊)** — https://www.youtube.com/@jmsdfmsopao
- **Japan — Ministry of Defense (防衛省)** — https://www.youtube.com/@modchannel
- **North Korea / DPRK Monitoring — Radio Free Asia Korean** — https://www.youtube.com/@RFAVideo
- **North Korea / DPRK Monitoring — VOA Korean** — https://www.youtube.com/@voakorea
- **Philippines — ABS-CBN News** — https://www.youtube.com/@ABSCBNNews
- **Philippines — GMA News Online** — https://www.youtube.com/@gmanews
- **Philippines — News5 / One News** — https://www.youtube.com/@News5Everywhere
- **Philippines — Presidential Communications Office (PCO)** — https://www.youtube.com/@PresidentialCommunicationsOffice
- **Philippines — Radio Television Malacañang (RTVM)** — https://www.youtube.com/@RTVMalacanang
- **Philippines — Rappler** — https://www.youtube.com/@Rappler
- **Philippines — Supreme Court of the Philippines** — https://www.youtube.com/@SupremeCourtPH
- **South Korea — JTBC News** — https://www.youtube.com/@JTBC_news
- **South Korea — KBS News** — https://www.youtube.com/@newskbs
- **South Korea — MBC News** — https://www.youtube.com/@MBCNEWS11
- **South Korea — Newstapa (뉴스타파)** — https://www.youtube.com/@newstapa
- **South Korea — OhmyNews (오마이뉴스)** — https://www.youtube.com/@OhmynewsTV
- **South Korea — Pennmike (펜앤드마이크)** — https://www.youtube.com/@pennmike
- **South Korea — SBS News** — https://www.youtube.com/@SBSnews8
- **South Korea — YTN** — https://www.youtube.com/@YTN
- **South Korea — Yonhap News TV (연합뉴스TV)** — https://www.youtube.com/@yonhapnewstv23
- **South Korea — 고성국TV** — https://www.youtube.com/@kosungkuk
- **South Korea — 김어준의 겸손은힘들다 뉴스공장** — https://www.youtube.com/@gyeomsonisnothing
- **South Korea — 뉴스타파** — https://www.youtube.com/@newstapa
- **South Korea — 성창경TV** — https://www.youtube.com/@sungchangkyung
- **South Korea — 신의한수** — https://www.youtube.com/@shinuihansu
- **South Korea — 오마이TV** — https://www.youtube.com/@OhmynewsTV
- **South Korea — 펜앤드마이크TV** — https://www.youtube.com/@pennmike
- **Taiwan — EBC News (東森新聞)** — https://www.youtube.com/@newsebc
- **Taiwan — Formosa TV News (民視新聞)** — https://www.youtube.com/@FTVNews
- **Taiwan — SET News (三立新聞網)** — https://www.youtube.com/@setn
- **Taiwan — TVBS News** — https://www.youtube.com/@TVBSNEWS01
- **Taiwan — TaiwanPlus** — https://www.youtube.com/@TaiwanPlus
- **United States — ABC News** — https://www.youtube.com/@ABCNews
- **United States — Atlantic Council** — https://www.youtube.com/@AtlanticCouncilUS
- **United States — Breitbart News** — https://www.youtube.com/@BreitbartNews
- **United States — CBS News** — https://www.youtube.com/@CBSNews
- **United States — CISA** — https://www.youtube.com/@CISAgov
- **United States — CNN** — https://www.youtube.com/@CNN
- **United States — CSIS** — https://www.youtube.com/@csis
- **United States — Council on Foreign Relations** — https://www.youtube.com/@cfr
- **United States — Department of Justice** — https://www.youtube.com/@TheJusticeDepartment
- **United States — Federal Bureau of Investigation** — https://www.youtube.com/@FBI
- **United States — Fox News** — https://www.youtube.com/@FoxNews
- **United States — NBC News** — https://www.youtube.com/@NBCNews
- **United States — NPR** — https://www.youtube.com/@NPR
- **United States — National Review** — https://www.youtube.com/@nationalreview
- **United States — PBS NewsHour** — https://www.youtube.com/@PBSNewsHour
- **United States — Politico** — https://www.youtube.com/@POLITICO
- **United States — ProPublica** — https://www.youtube.com/@propublica
- **United States — RAND Corporation** — https://www.youtube.com/@RANDCorporation
- **United States — The Hill** — https://www.youtube.com/@thehill
- **United States — U.S. Air Force** — https://www.youtube.com/@usairforce
- **United States — U.S. Army** — https://www.youtube.com/@USArmy
- **United States — U.S. Coast Guard** — https://www.youtube.com/@USCG
- **United States — U.S. Department of Defense** — https://www.youtube.com/@DeptofDefense
- **United States — U.S. Department of State** — https://www.youtube.com/@StateDept
- **United States — U.S. Marine Corps** — https://www.youtube.com/@marines
- **United States — U.S. Navy** — https://www.youtube.com/@USNavy
- **United States — White House** — https://www.youtube.com/@WhiteHouse

# Difficult or Technically Problematic Sources

- **China — 36Kr (36氪)** — JS-heavy/app-centric; anti-bot possible. — Primary method: Playwright
- **China — CGTN** — Video-first; site may be JS-heavy. — Primary method: YouTube/yt-dlp
- **China — Caixin (财新)** — Strong paywall; subscription/session needed. — Primary method: Direct scraping
- **China — Center for China and Globalization (CCG)** — Low-volume, report/event-heavy; some sites have inconsistent accessibility. — Primary method: Direct scraping
- **China — China Digital Times** — Blocked in mainland China. — Primary method: Native RSS
- **China — China Institute of International Studies (CIIS)** — Low-volume, report/event-heavy; some sites have inconsistent accessibility. — Primary method: changedetection.io
- **China — China Institutes of Contemporary International Relations (CICIR)** — Low-volume, report/event-heavy; some sites have inconsistent accessibility. — Primary method: changedetection.io
- **China — Chinese Academy of Social Sciences (CASS)** — Low-volume, report/event-heavy; some sites have inconsistent accessibility. — Primary method: changedetection.io
- **China — Fudan University Institute of International Studies** — Low-volume, report/event-heavy; some sites have inconsistent accessibility. — Primary method: changedetection.io
- **China — Huxiu (虎嗅)** — Membership content; JS-heavy. — Primary method: Playwright
- **China — Jiemian News (界面新闻)** — JS-heavy. — Primary method: Playwright
- **China — LatePost (晚点)** — Some subscription/app-first content. — Primary method: Direct scraping
- **China — Peking University Institute of International and Strategic Studies** — Low-volume, report/event-heavy; some sites have inconsistent accessibility. — Primary method: changedetection.io
- **China — Shanghai Institutes for International Studies (SIIS)** — Low-volume, report/event-heavy; some sites have inconsistent accessibility. — Primary method: Direct scraping
- **China — Southern Weekly (南方周末)** — Censorship constraints; paywall may apply. — Primary method: Direct scraping
- **China — The Paper (澎湃新闻)** — JavaScript-heavy/anti-bot. — Primary method: Playwright
- **China — Tsinghua Center for International Security and Strategy** — Low-volume, report/event-heavy; some sites have inconsistent accessibility. — Primary method: changedetection.io
- **Indo-Pacific / Regional — BenarNews** — Blocked in some countries; feed structures vary. — Primary method: Direct scraping
- **Indo-Pacific / Regional — ISEAS – Yusof Ishak Institute** — Some publications/paywall. — Primary method: Direct scraping
- **Indo-Pacific / Regional — Janes** — Hard paywall/licensing; subscription integration preferable. — Primary method: Direct scraping
- **Indo-Pacific / Regional — Radio Free Asia** — Blocked in target countries; language-service structures vary. — Primary method: YouTube/yt-dlp
- **Indo-Pacific / Regional — South China Morning Post** — Paywall/anti-bot; licensed access may be preferable. — Primary method: Direct scraping
- **Indo-Pacific / Regional — The Straits Times** — Paywall on many stories. — Primary method: Direct scraping
- **Indo-Pacific / Regional — U.S. Embassy Beijing** — Blocked inside China in some contexts. — Primary method: changedetection.io
- **Japan — Asahi Shimbun (朝日新聞)** — Paywall and robots/anti-bot. — Primary method: Playwright
- **Japan — Bunshun Online (文春オンライン)** — Paywall/member content; tabloid mix. — Primary method: Direct scraping
- **Japan — Diamond Online (ダイヤモンド・オンライン)** — Paywall/premium content. — Primary method: Direct scraping
- **Japan — Hokkaido Shimbun (北海道新聞)** — Paywall possible. — Primary method: Direct scraping
- **Japan — Kyodo News (共同通信)** — Public full-text limited; licensing may be preferable. — Primary method: Direct scraping
- **Japan — Mainichi Shimbun (毎日新聞)** — Metered/paywalled. — Primary method: Direct scraping
- **Japan — Nikkei (日本経済新聞)** — Strong paywall; licensed access preferable. — Primary method: Direct scraping
- **Japan — Nikkei Asia** — Paywall. — Primary method: Direct scraping
- **Japan — Nishinippon Shimbun (西日本新聞)** — Paywall on some content. — Primary method: Direct scraping
- **Japan — Okinawa Times (沖縄タイムス)** — Robots/access restrictions and paywalled items. — Primary method: Playwright
- **Japan — Sankei Shimbun (産経新聞)** — Robots/access limits. — Primary method: Playwright
- **Japan — The Japan Times** — Subscription/paywall on some content. — Primary method: Native RSS
- **Japan — Tokyo Shimbun (東京新聞)** — Some paywall. — Primary method: Direct scraping
- **Japan — Yomiuri Shimbun (読売新聞)** — Paywall/membership on some content. — Primary method: Direct scraping
- **North Korea / DPRK Monitoring — DPRK Ministry of Foreign Affairs** — Intermittent access; low-volume high-value. — Primary method: changedetection.io
- **North Korea / DPRK Monitoring — Korea Risk Group** — Subscription/commercial access. — Primary method: Direct scraping
- **North Korea / DPRK Monitoring — Korean Central News Agency (KCNA)** — Intermittent accessibility, DNS/TLS/geoblocking; retries/snapshots needed. — Primary method: Direct scraping
- **North Korea / DPRK Monitoring — NK News** — Strong paywall; subscription/session handling required. — Primary method: Direct scraping
- **North Korea / DPRK Monitoring — NK Pro** — Hard paywall/subscription and licensing constraints. — Primary method: Direct scraping
- **North Korea / DPRK Monitoring — Radio Free Asia Korean** — Blocked in some target environments; use web plus video/audio. — Primary method: YouTube/yt-dlp
- **North Korea / DPRK Monitoring — Rodong Sinmun (로동신문)** — Intermittent .kp accessibility; archive every version. — Primary method: Direct scraping
- **North Korea / DPRK Monitoring — Voice of Korea** — Audio/media extraction and intermittent access. — Primary method: Direct scraping
- **Philippines — Commission on Elections (COMELEC)** — Automated access can be unreliable. — Primary method: Playwright
- **Philippines — Department of Foreign Affairs (DFA)** — Automated access may be inconsistent. — Primary method: changedetection.io
- **Philippines — Department of National Defense (DND)** — Access can be inconsistent. — Primary method: changedetection.io
- **Philippines — Office of the President of the Philippines** — Automated access may return 403/WAF. — Primary method: Playwright
- **Philippines — Official Gazette of the Republic of the Philippines** — Automated access can be blocked/403. — Primary method: Playwright
- **Philippines — Radio Television Malacañang (RTVM)** — Captions inconsistent; ASR fallback useful. — Primary method: YouTube/yt-dlp
- **Philippines — Rappler** — Robots/anti-bot may affect crawlers; feed health-check. — Primary method: Native RSS
- **Philippines — The Manila Times** — Paywall/subscription on some content. — Primary method: Direct scraping
- **South Korea — Chosun Ilbo (조선일보)** — Some paywall/anti-bot; multilingual editions. — Primary method: Direct scraping
- **South Korea — Hankyoreh (한겨레)** — Robots/site access can complicate scraping. — Primary method: Direct scraping
- **South Korea — JoongAng Ilbo (중앙일보)** — Robots/anti-bot restrictions observed. — Primary method: Playwright
- **South Korea — Korea Economic Daily (한국경제)** — Some subscription products. — Primary method: Direct scraping
- **South Korea — News1 Korea (뉴스1)** — Robots/access restrictions may require browser/licensed access. — Primary method: Direct scraping
- **South Korea — Yonhap News Agency (연합뉴스)** — Robots/anti-bot restrictions; licensed/API access may be preferable. — Primary method: Direct scraping
- **Taiwan — CommonWealth Magazine (天下雜誌)** — Premium paywall. — Primary method: Direct scraping
- **Taiwan — DigiTimes** — Subscription/paywall; licensed access may be needed. — Primary method: Direct scraping
- **Taiwan — TaiwanPlus** — Video-first; site may be JS-heavy. — Primary method: YouTube/yt-dlp
- **United States — Associated Press (AP)** — Public feeds limited; licensing terms matter for full-text reuse. — Primary method: Direct scraping
- **United States — Bloomberg** — Strong paywall/anti-bot; licensed/API access preferable. — Primary method: Direct scraping
- **United States — CNN** — Legacy RSS endpoints can be inconsistent; health-check. — Primary method: Native RSS
- **United States — Foreign Affairs** — Paywall/subscription may apply. — Primary method: Direct scraping
- **United States — Foreign Policy** — Paywall/subscription may apply. — Primary method: Direct scraping
- **United States — Politico** — Premium products paywalled. — Primary method: Native RSS
- **United States — Reuters U.S.** — Public RSS limited; licensing/redistribution restrictions; licensed/API access preferable. — Primary method: Direct scraping
- **United States — The Atlantic** — Some subscription/paywall or membership content may apply. — Primary method: Direct scraping
- **United States — The Daily Wire** — Some subscription/paywall or membership content may apply. — Primary method: Direct scraping
- **United States — The New York Times** — Metered/paywalled; feed usually discovery/summary. — Primary method: Native RSS
- **United States — The Wall Street Journal** — Hard paywall/anti-bot; licensed access preferable. — Primary method: Direct scraping
- **United States — The Washington Post** — Paywall; category RSS available; full text may require subscription session. — Primary method: Native RSS

## Cross-cutting technical problems

- **Licensing / full-text rights:** Reuters, AP, Bloomberg, Janes and many newspapers may require licensed access for scalable full-text ingestion or redistribution. RSS availability is not a republication license.
- **Hard paywalls:** WSJ, Bloomberg, Nikkei/Nikkei Asia, SCMP, Caixin, Janes, NK News/NK Pro and other premium outlets need subscription-aware session handling or licensed feeds.
- **Anti-bot / WAF / robots:** several Korean, Japanese and Philippine publishers and government sites resist ordinary automated clients. Use Playwright only after simple HTTP retrieval fails.
- **DPRK connectivity:** `.kp` domains can be intermittent or regionally unreachable. Implement retries, long polling intervals, document snapshots and alternate lawful mirrors.
- **China content mutation/deletion:** store `document_versions`, retrieval timestamps, hashes and snapshots so later edits or deletions are detectable.
- **Government document formats:** expect PDF, HWP/HWPX, scanned PDF and image-based releases; add parsers/OCR fallback.
- **YouTube captions:** captions can be missing or disabled; follow human subtitles → YouTube automatic captions → local ASR.
- **Feed health:** validate XML, item recency, ETag/Last-Modified behavior and stale-feed thresholds before declaring a feed production-ready.

# Suggested Web UI Folder / Category Structure

```text
Dashboard
Breaking
Stories
Documents
Alerts
Sources
├── United States
├── South Korea
├── Japan
├── Taiwan
├── China
├── North Korea
├── Philippines
└── Indo-Pacific
    ├── Major National News
    ├── Regional & Local
    ├── Independent & Investigative
    ├── Political Perspectives
    ├── Business & Financial
    ├── Defense & Military
    ├── Foreign Policy & Geopolitics
    ├── Technology & Cybersecurity
    ├── Judiciary & Legal
    ├── Elections
    ├── Executive / Government
    ├── Legislatures
    ├── Courts
    ├── Election Commissions
    ├── Defense / Military Branches
    ├── Foreign Ministries
    ├── Intelligence / National Security
    ├── Police / Law Enforcement
    ├── Think Tanks / Research / Universities
    ├── Embassies / International Organizations
    └── YouTube
Feed Operations
├── Native RSS / Atom
├── RSSHub
├── RSS-Bridge
├── Direct Scraping
├── Playwright
├── changedetection.io
└── YouTube / yt-dlp
Source Health
├── Healthy
├── Stale
├── Parse Failure
├── Paywall / Authentication
├── WAF / Anti-bot
└── Disabled
Topics
Monitors
Entities
Search
AI Analysis
System
```

# Recommended Source-Onboarding Health Checks

Before a source moves from inventory to production, record: final canonical URL; HTTP status; robots/terms review; feed XML validity; latest-item age; average item cadence; ETag/Last-Modified support; article-body extraction success; JS requirement; paywall/auth requirement; language; timezone; date parser; canonical URL behavior; duplicate rate; and a sample of 20–50 documents for parser regression tests.
