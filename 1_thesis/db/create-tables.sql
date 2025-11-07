CREATE TABLE district (
	id SERIAL4 NOT NULL,
	"name" TEXT NOT NULL,
	PRIMARY KEY (id)
);

CREATE TABLE patient (
	id SERIAL4 NOT NULL,
	import_id TEXT NOT NULL,
	gender TEXT,
	birthday DATE,
	district_id INT4,
	PRIMARY KEY (id),
	FOREIGN KEY (district_id) REFERENCES district(id)
);

CREATE TABLE analysis (
	id SERIAL4 NOT NULL,
	"name" TEXT NOT NULL,
	PRIMARY KEY (id)
);

CREATE TABLE test (
	id SERIAL4 NOT NULL,
	"name" TEXT NOT NULL,
	mnemonic TEXT,
	analysis_id INT4 NOT NULL,
	PRIMARY KEY (id),
	FOREIGN KEY (analysis_id) REFERENCES analysis(id)
);

CREATE TABLE mkb (
    id INT4 NOT NULL,
    code TEXT NOT NULL,
    "name" TEXT NOT NULL,
    parent_id INT4,
    "level" INT4 NOT NULL,
    PRIMARY KEY (id),
    FOREIGN KEY (parent_id) REFERENCES mkb(id)
);

CREATE TABLE referral_header (
	id SERIAL4 NOT NULL,
	import_id TEXT NOT NULL,
	patient_id INT4 NOT NULL,
	diagnosis_id INT4,
	PRIMARY KEY (id),
	FOREIGN KEY (patient_id) REFERENCES patient(id),
	FOREIGN KEY (diagnosis_id) REFERENCES mkb(id)
);

CREATE TABLE referral_body (
	id SERIAL4 NOT NULL,
	referral_header_id INT4 NOT NULL,
	sampling_date DATE NOT NULL,
	test_id INT4 NOT NULL,
	result FLOAT8,
	patient_age_when_sampling INT4 NOT NULL,
	PRIMARY KEY (id),
	FOREIGN KEY (referral_header_id) REFERENCES referral_header(id),
	FOREIGN KEY (test_id) REFERENCES test(id)
);
