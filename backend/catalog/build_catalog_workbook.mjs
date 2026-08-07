import { createRequire } from "node:module";
import fs from "node:fs/promises";
import path from "node:path";

const require = createRequire(import.meta.url);
const { FileBlob, SpreadsheetFile, Workbook } = require("@oai/artifact-tool");

const cwd = process.cwd();
const publicCatalog = path.resolve(cwd, "..", "opensource-for-business", "src", "data");
const workbookPath = path.resolve(cwd, "backend", "catalog", "software_catalog.xlsx");
const outputPath = path.resolve(cwd, "outputs", "software_catalog.xlsx");
const readJson = async (name) => JSON.parse(await fs.readFile(path.join(publicCatalog, name), "utf8"));
const join = (values) => (values ?? []).join(" | ");

async function rowsFromExisting(sheetName) {
  try {
    const blob = await FileBlob.load(workbookPath);
    const existing = await SpreadsheetFile.importXlsx(blob);
    const values = existing.worksheets.getItem(sheetName).getUsedRange(true).values;
    const headers = values[0].map((value) => String(value));
    return values.slice(1).filter((row) => row.some((value) => value !== null && value !== "")).map((row) => Object.fromEntries(headers.map((header, index) => [header, row[index]])));
  } catch {
    return [];
  }
}

const [projects, departments, licenses, snapshots, useCases, oldProducts, oldCategories] = await Promise.all([
  readJson("projects.json"), readJson("departments.json"), readJson("licenses.json"), readJson("repo-snapshots.json"), readJson("business-use-cases.json"), rowsFromExisting("Products"), rowsFromExisting("Categories"),
]);

const oldProductMap = new Map(oldProducts.map((item) => [item.slug, item]));
const oldCategoryMap = new Map(oldCategories.map((item) => [item.id, item]));
const useCasesByProject = new Map();
for (const useCase of useCases) for (const slug of useCase.projectSlugs) useCasesByProject.set(slug, [...(useCasesByProject.get(slug) ?? []), useCase]);

const categorySignals = {
  "smart-city-platforms": ["48000000 | 72212000 | 72316000", "smart city platform | urban data platform | context broker | city platform", "πλατφόρμα έξυπνης πόλης | αστικά δεδομένα | μεσίτης περιεχομένου | διαλειτουργικότητα", "hardware only | μόνο προμήθεια εξοπλισμού"],
  "iot-sensor-management": ["32235000 | 32440000 | 72212461", "IoT | sensor management | telemetry | device management | remote monitoring", "διαδίκτυο πραγμάτων | αισθητήρες | τηλεμετρία | διαχείριση συσκευών | απομακρυσμένη παρακολούθηση", "sensor purchase only | μόνο αγορά αισθητήρων"],
  "urban-operations-centers": ["48820000 | 72212000 | 72316000", "operations center | command center | situational awareness | urban operations", "κέντρο λειτουργίας | κέντρο ελέγχου | επιχειρησιακή εικόνα | αστικές λειτουργίες", "building construction | κατασκευή κτιρίου"],
  "public-wifi-network-access": ["32412110 | 32418000 | 32510000 | 72700000", "public wifi | wireless network | captive portal | guest access | network controller", "δημόσιο wifi | ασύρματο δίκτυο | πύλη επισκεπτών | πρόσβαση δικτύου | διαχείριση δικτύου", "mobile subscriptions only | μόνο τηλεφωνικές συνδέσεις"],
  "geospatial-data-platforms": ["38221000 | 71354100 | 72316000", "GIS | geospatial data | spatial data infrastructure | mapping | map server", "γεωγραφικό σύστημα πληροφοριών | γεωχωρικά δεδομένα | χωρικά δεδομένα | χαρτογράφηση", "paper maps only | μόνο έντυποι χάρτες"],
  "fleet-telematics": ["34100000 | 50111100 | 72212461", "fleet telematics | GPS tracking | vehicle tracking | geofence | trip monitoring", "τηλεματική στόλου | παρακολούθηση οχημάτων | GPS | γεωπερίφραξη | διαδρομές", "vehicle purchase only | μόνο αγορά οχημάτων"],
  "fleet-operations-maintenance": ["50110000 | 50111100 | 72212461", "fleet management | vehicle maintenance | workshop management | vehicle registry", "διαχείριση στόλου | συντήρηση οχημάτων | γραφείο κίνησης | μητρώο οχημάτων", "fuel supply only | μόνο προμήθεια καυσίμων"],
  "route-logistics-optimization": ["63712000 | 72212461 | 71311200", "route optimization | vehicle routing | logistics planning | time windows", "βελτιστοποίηση δρομολογίων | σχεδιασμός διαδρομών | logistics | χρονικά παράθυρα", "road construction | κατασκευή οδών"],
  "smart-parking": ["38730000 | 63712400 | 72212461", "smart parking | controlled parking | parking availability | parking permits", "έξυπνη στάθμευση | ελεγχόμενη στάθμευση | διαθεσιμότητα θέσεων | άδειες στάθμευσης", "parking construction only | κατασκευή χώρου στάθμευσης"],
  "ev-charging": ["31158000 | 31681500 | 72212461", "EV charging | charge point management | OCPP | charging station", "ηλεκτροφόρτιση | διαχείριση φορτιστών | OCPP | σταθμός φόρτισης", "electricity supply only | μόνο προμήθεια ηλεκτρικής ενέργειας"],
  "accessible-mobility": ["63712000 | 72212461 | 71354100", "accessible routing | wheelchair routing | inclusive mobility | journey planning", "προσβάσιμη δρομολόγηση | μετακίνηση ΑμεΑ | προσβάσιμη κινητικότητα | σχεδιασμός ταξιδιού", "vehicle purchase only | μόνο αγορά οχημάτων"],
  "energy-management": ["71314200 | 38551000 | 72212461", "energy management | energy monitoring | building energy | consumption analytics", "διαχείριση ενέργειας | ενεργειακή παρακολούθηση | δημόσια κτίρια | ανάλυση κατανάλωσης", "energy certificate only | μόνο ενεργειακό πιστοποιητικό"],
  "environmental-monitoring": ["90711500 | 90731100 | 38420000", "environmental monitoring | weather data | air quality | sensor observations", "περιβαλλοντική παρακολούθηση | μετεωρολογικά δεδομένα | ποιότητα αέρα | παρατηρήσεις αισθητήρων", "laboratory consumables only | μόνο εργαστηριακά αναλώσιμα"],
  "water-utility-metering": ["38421100 | 65100000 | 72212461", "smart water meters | water metering | leak detection | remote meter reading", "έξυπνα υδρόμετρα | μέτρηση νερού | ανίχνευση διαρροών | τηλεμέτρηση", "meter purchase only | μόνο αγορά υδρομέτρων"],
  "waste-recycling-operations": ["90511000 | 90514000 | 72212461", "waste collection | recycling operations | bin fill level | smart bins", "αποκομιδή απορριμμάτων | ανακύκλωση | πληρότητα κάδων | έξυπνοι κάδοι", "bin purchase only | μόνο αγορά κάδων"],
  "urban-green-assets": ["77211500 | 77310000 | 71354100", "urban forestry | tree inventory | green assets | park maintenance", "αστικό πράσινο | μητρώο δέντρων | πράσινες υποδομές | συντήρηση πάρκων", "plant supply only | μόνο προμήθεια φυτών"],
  "civic-services-enforcement": ["75242110 | 72212461 | 72320000", "civic service request | municipal enforcement | citation management | field inspection", "αιτήματα πολιτών | δημοτική αστυνομία | έκδοση κλήσεων | επιτόπιος έλεγχος", "security guards only | μόνο υπηρεσίες φύλαξης"],
  "digital-participation": ["75130000 | 72212461 | 72413000", "public consultation | citizen participation | participatory budgeting | proposals", "δημόσια διαβούλευση | συμμετοχή πολιτών | συμμετοχικός προϋπολογισμός | προτάσεις", "opinion poll only | μόνο δημοσκόπηση"],
  "emergency-crisis-management": ["75252000 | 72212461 | 48820000", "civil protection | emergency management | crisis coordination | incident resources", "πολιτική προστασία | διαχείριση έκτακτης ανάγκης | συντονισμός κρίσης | πόροι συμβάντος", "insurance only | μόνο ασφάλιση"],
  "wildfire-detection": ["75251110 | 90711500 | 32235000", "wildfire detection | forest fire prevention | smoke detection | early warning", "δασικές πυρκαγιές | πρόληψη πυρκαγιάς | ανίχνευση καπνού | έγκαιρη προειδοποίηση", "firefighting vehicle purchase only | μόνο αγορά πυροσβεστικού οχήματος"],
  "cultural-heritage": ["92520000 | 48190000 | 72212311", "cultural heritage repository | digital collection | museum catalog | archive metadata", "πολιτιστικό αποθετήριο | ψηφιακή συλλογή | μουσειακός κατάλογος | μεταδεδομένα αρχείου", "digitization equipment only | μόνο εξοπλισμός ψηφιοποίησης"],
  "library-management": ["48161000 | 92511000 | 72212311", "library management system | cataloging | circulation | patron management", "σύστημα βιβλιοθήκης | καταλογογράφηση | δανεισμός | διαχείριση μελών", "book supply only | μόνο προμήθεια βιβλίων"],
  "community-events-ticketing": ["79952000 | 72212461 | 72413000", "event management | ticketing | registration | community calendar", "διαχείριση εκδηλώσεων | εισιτήρια | εγγραφές | ημερολόγιο δράσεων", "venue rental only | μόνο ενοικίαση χώρου"],
  "volunteering-community-crm": ["48445000 | 75130000 | 72212461", "volunteer registry | community CRM | constituent management | volunteer skills", "μητρώο εθελοντών | κοινωνικό CRM | διαχείριση επαφών | δεξιότητες εθελοντών", "staff recruitment only | μόνο πρόσληψη προσωπικού"],
  "city-guides-public-maps": ["71354100 | 72413000 | 72212326", "digital city guide | public map | points of interest | visitor routes", "ψηφιακός οδηγός πόλης | δημόσιος χάρτης | σημεία ενδιαφέροντος | διαδρομές επισκεπτών", "printed guide only | μόνο έντυπος οδηγός"],
};

const flatCategories = departments.flatMap((department) => department.categories.map((category) => {
  const previous = oldCategoryMap.get(category.id);
  const signals = categorySignals[category.id];
  return {
    id:category.id, department_id:department.id, name:category.name, description:category.description,
    cpv_prefixes:signals?.[0] ?? previous?.cpv_prefixes ?? "",
    keywords_en:signals?.[1] ?? previous?.keywords_en ?? category.name,
    keywords_el:signals?.[2] ?? previous?.keywords_el ?? "",
    negative_keywords:signals?.[3] ?? previous?.negative_keywords ?? "hardware only | licenses only",
  };
}));

const productHeaders = ["slug","name","edition","repository","website","summary","problem","ideal_for","department_ids","category_ids","buyer_roles","company_sizes","deployment_modes","service_types","license_id","maturity","solution_type","editorial_score","english_support","greek_support","greek_evidence","edition_boundary","featured","last_verified_at","extra_keywords_en","extra_keywords_el","negative_keywords","delivery_fit","active"];
const productRows = projects.map((project) => {
  const previous = oldProductMap.get(project.slug) ?? {};
  const related = useCasesByProject.get(project.slug) ?? [];
  return productHeaders.map((header) => ({
    slug:project.slug, name:project.name, edition:project.edition, repository:project.repository, website:project.website,
    summary:project.summary, problem:project.problem, ideal_for:project.idealFor, department_ids:join(project.departmentIds), category_ids:join(project.categoryIds),
    buyer_roles:join(project.buyerRoles), company_sizes:join(project.companySizes), deployment_modes:join(project.deploymentModes), service_types:join(project.serviceTypes),
    license_id:project.licenseId, maturity:project.maturity, solution_type:project.solutionType ?? "production-platform", editorial_score:project.editorialScore,
    english_support:project.englishSupport, greek_support:project.greekSupport, greek_evidence:project.greekEvidence ?? "", edition_boundary:project.editionBoundary ?? "",
    featured:Boolean(project.featured), last_verified_at:project.lastVerifiedAt,
    extra_keywords_en:previous.extra_keywords_en ?? join(related.map((item) => item.title.en)),
    extra_keywords_el:previous.extra_keywords_el ?? join(related.map((item) => item.title.el)),
    negative_keywords:previous.negative_keywords ?? "hardware only | licenses only", delivery_fit:previous.delivery_fit ?? (project.solutionType === "reference-implementation" ? "partner_required" : "small_team"), active:previous.active ?? true,
  })[header]);
});

const departmentHeaders = ["id","name","short_name","description","icon"];
const departmentRows = departments.map((item) => [item.id,item.name,item.shortName,item.description,item.icon]);
const categoryHeaders = ["id","department_id","name","description","cpv_prefixes","keywords_en","keywords_el","negative_keywords"];
const categoryRows = flatCategories.map((item) => categoryHeaders.map((header) => item[header]));
const licenseHeaders = ["id","spdx","name","family","osi_approved","summary","obligations","evidence"];
const licenseRows = licenses.map((item) => [item.id,item.spdx,item.name,item.family,item.osiApproved,item.summary,join(item.obligations),item.evidence]);
const healthHeaders = ["slug","repo","stars","latest_release","last_activity","archived","observed_license","license_drift","verified_at","status"];
const healthRows = snapshots.map((item) => [item.slug,item.repo,item.stars,item.latestRelease,item.lastActivity ? new Date(item.lastActivity) : null,item.archived,item.observedLicense,item.licenseDrift,new Date(item.verifiedAt),item.status]);
const useCaseHeaders = ["slug","title_en","title_el","description_en","description_el","business_problem_en","business_problem_el","department_id","category_ids","fit","status"];
const useCaseRows = useCases.map((item) => [item.slug,item.title.en,item.title.el,item.description.en,item.description.el,item.businessProblem.en,item.businessProblem.el,item.departmentId,join(item.categoryIds),item.fit,item.status]);
const relationHeaders = ["use_case_slug","project_slug","rank","fit","rationale_en","rationale_el"];
const relationRows = useCases.flatMap((item) => item.projectSlugs.map((projectSlug, index) => [item.slug,projectSlug,index + 1,item.fit,`${projects.find((project) => project.slug === projectSlug)?.name} is mapped as a ${item.fit} implementation option for this business need.`,`${projects.find((project) => project.slug === projectSlug)?.name} αντιστοιχίζεται ως λύση επιπέδου ${item.fit} για τη συγκεκριμένη επιχειρηματική ανάγκη.`]));
const dictionaryHeaders = ["key","value","description"];
const dictionaryRows = [
  ["schema_version",2,"Workbook and runtime JSON schema version."],
  ["catalog_name","Opportunity Finder Open Source Catalog","Independent source of truth for Opportunity Finder matching."],
  ["snapshot_date","2026-08-06","Editorial and repository snapshot date."],
  ["ownership","Opportunity Finder","The application reads only the generated JSON snapshot compiled from this workbook."],
  ["products_count",projects.length,"Required Products row count."],
  ["departments_count",departments.length,"Required Departments row count."],
  ["categories_count",flatCategories.length,"Required Categories row count."],
  ["licenses_count",licenses.length,"Required Licenses row count."],
  ["repository_health_count",snapshots.length,"Required Repository Health row count."],
  ["business_use_cases_count",useCases.length,"Required Business Use Cases row count."],
  ["use_case_solutions_count",relationRows.length,"Required Use Case Solutions row count."],
  ["multi_value_delimiter","|","Use the pipe delimiter with spaces around it in multi-value cells."],
  ["solution_type","production-platform | specialist-component | reference-implementation","Delivery maturity and architectural role."],
  ["use_case_fit","direct | partial | foundation","Strength of the use-case-to-solution mapping."],
  ["maintenance","Edit this workbook, then run python -m app.catalog_import","The workbook is the maintained catalog; runtime JSON is generated."],
];

const workbook = Workbook.create();
const navy = "#183A59";
const stripe = "#D8F0FA";
const border = "#9FCFE1";

function colLetter(index) {
  let output = "";
  for (let value = index; value > 0; value = Math.floor((value - 1) / 26)) output = String.fromCharCode(65 + ((value - 1) % 26)) + output;
  return output;
}

function addSheet(name, headers, rows, tableName, widths = {}) {
  const sheet = workbook.worksheets.add(name);
  sheet.showGridLines = true;
  const endCol = colLetter(headers.length);
  const values = [headers, ...rows];
  const used = sheet.getRange(`A1:${endCol}${values.length}`);
  used.values = values;
  used.format = { font:{ name:"Aptos", size:10, color:"#183042" }, verticalAlignment:"top", borders:{ top:{color:border,style:"continuous"}, bottom:{color:border,style:"continuous"}, left:{color:border,style:"continuous"}, right:{color:border,style:"continuous"} } };
  const header = sheet.getRange(`A1:${endCol}1`);
  header.format = { fill:navy, font:{ name:"Aptos Display", size:10, bold:true, color:"#FFFFFF" }, rowHeight:28, verticalAlignment:"center" };
  for (let row = 2; row <= values.length; row += 2) sheet.getRange(`A${row}:${endCol}${row}`).format.fill = stripe;
  sheet.getRange(`A2:${endCol}${values.length}`).format.rowHeight = 22;
  sheet.freezePanes.freezeRows(1);
  sheet.tables.add(`A1:${endCol}${values.length}`, true, tableName);
  for (const [column, width] of Object.entries(widths)) sheet.getRange(`${column}1:${column}${values.length}`).format.columnWidth = width;
  return sheet;
}

const productsSheet = addSheet("Products",productHeaders,productRows,"ProductsTable",{A:20,B:22,C:18,D:36,E:30,F:48,G:48,H:42,I:28,J:30,K:28,L:26,M:25,N:32,O:16,P:16,Q:24,R:12,S:14,T:14,U:28,V:42,W:12,X:16,Y:34,Z:34,AA:30,AB:18,AC:10});
productsSheet.getRange(`F2:H${productRows.length + 1}`).format.wrapText = true;
const departmentsSheet = addSheet("Departments",departmentHeaders,departmentRows,"DepartmentsTable",{A:28,B:34,C:24,D:65,E:16});
departmentsSheet.getRange(`D2:D${departmentRows.length + 1}`).format.wrapText = true;
const categoriesSheet = addSheet("Categories",categoryHeaders,categoryRows,"CategoriesTable",{A:30,B:30,C:34,D:56,E:35,F:55,G:55,H:45});
categoriesSheet.getRange(`D2:H${categoryRows.length + 1}`).format.wrapText = true;
const licensesSheet = addSheet("Licenses",licenseHeaders,licenseRows,"LicensesTable",{A:18,B:22,C:30,D:22,E:14,F:62,G:60,H:40});
licensesSheet.getRange(`F2:H${licenseRows.length + 1}`).format.wrapText = true;
const healthSheet = addSheet("Repository Health",healthHeaders,healthRows,"RepositoryHealthTable",{A:24,B:36,C:14,D:20,E:24,F:12,G:22,H:16,I:24,J:20});
healthSheet.getRange(`E2:E${healthRows.length + 1}`).format.numberFormat = "yyyy-mm-dd hh:mm:ss";
healthSheet.getRange(`I2:I${healthRows.length + 1}`).format.numberFormat = "yyyy-mm-dd hh:mm:ss";
const useCasesSheet = addSheet("Business Use Cases",useCaseHeaders,useCaseRows,"BusinessUseCasesTable",{A:32,B:40,C:42,D:58,E:58,F:65,G:65,H:30,I:38,J:16,K:14});
useCasesSheet.getRange(`B2:G${useCaseRows.length + 1}`).format.wrapText = true;
const relationsSheet = addSheet("Use Case Solutions",relationHeaders,relationRows,"UseCaseSolutionsTable",{A:34,B:26,C:10,D:16,E:66,F:66});
relationsSheet.getRange(`E2:F${relationRows.length + 1}`).format.wrapText = true;
const dictionarySheet = addSheet("Data Dictionary",dictionaryHeaders,dictionaryRows,"DataDictionaryTable",{A:34,B:52,C:75});
dictionarySheet.getRange(`B2:C${dictionaryRows.length + 1}`).format.wrapText = true;

await fs.mkdir(path.dirname(outputPath), { recursive:true });
const xlsx = await SpreadsheetFile.exportXlsx(workbook);
await xlsx.save(workbookPath);
await xlsx.save(outputPath);
const inspect = await workbook.inspect({ kind:"workbook,sheet,table", maxChars:7000, tableMaxRows:3, tableMaxCols:5 });
console.log(inspect.ndjson ?? JSON.stringify(inspect));
console.log(JSON.stringify({ workbookPath, outputPath, counts:{ products:projects.length, departments:departments.length, categories:flatCategories.length, licenses:licenses.length, repositoryHealth:snapshots.length, businessUseCases:useCases.length, useCaseSolutions:relationRows.length } }));
