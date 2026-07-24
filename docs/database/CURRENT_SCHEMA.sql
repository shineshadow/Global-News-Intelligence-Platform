--
-- PostgreSQL database dump
--

\restrict 1Eg8aroonCWf9stJgpayKwlivgquL6tTAQh6mdIZqzWWIRlXFOMrWA2KbHUcVcf

-- Dumped from database version 17.10 (Debian 17.10-0+deb13u1)
-- Dumped by pg_dump version 17.10 (Debian 17.10-0+deb13u1)

SET statement_timeout = 0;
SET lock_timeout = 0;
SET idle_in_transaction_session_timeout = 0;
SET transaction_timeout = 0;
SET client_encoding = 'UTF8';
SET standard_conforming_strings = on;
SELECT pg_catalog.set_config('search_path', '', false);
SET check_function_bodies = false;
SET xmloption = content;
SET client_min_messages = warning;
SET row_security = off;

SET default_tablespace = '';

SET default_table_access_method = heap;

--
-- Name: alembic_version; Type: TABLE; Schema: public; Owner: news_intelligence_app
--

CREATE TABLE public.alembic_version (
    version_num character varying(32) NOT NULL
);


ALTER TABLE public.alembic_version OWNER TO news_intelligence_app;

--
-- Name: classification_runs; Type: TABLE; Schema: public; Owner: news_intelligence_app
--

CREATE TABLE public.classification_runs (
    id bigint NOT NULL,
    document_id bigint NOT NULL,
    pipeline_version character varying(100) NOT NULL,
    taxonomy_version character varying(50) NOT NULL,
    started_at timestamp with time zone DEFAULT now() NOT NULL,
    completed_at timestamp with time zone,
    status character varying(30) DEFAULT 'running'::character varying NOT NULL,
    language character varying(20),
    classifier_versions jsonb DEFAULT '{}'::jsonb NOT NULL,
    ruleset_version character varying(100),
    llm_provider character varying(100),
    llm_model character varying(255),
    input_hash character varying(64),
    output_hash character varying(64),
    error text,
    metadata jsonb DEFAULT '{}'::jsonb NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL,
    CONSTRAINT ck_classification_runs_completed_after_started CHECK (((completed_at IS NULL) OR (completed_at >= started_at)))
);


ALTER TABLE public.classification_runs OWNER TO news_intelligence_app;

--
-- Name: classification_runs_id_seq; Type: SEQUENCE; Schema: public; Owner: news_intelligence_app
--

CREATE SEQUENCE public.classification_runs_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.classification_runs_id_seq OWNER TO news_intelligence_app;

--
-- Name: classification_runs_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: news_intelligence_app
--

ALTER SEQUENCE public.classification_runs_id_seq OWNED BY public.classification_runs.id;


--
-- Name: document_entities; Type: TABLE; Schema: public; Owner: news_intelligence_app
--

CREATE TABLE public.document_entities (
    id bigint NOT NULL,
    confidence numeric(5,4) NOT NULL,
    classification_method character varying(50) NOT NULL,
    classifier_version character varying(255),
    classification_run_id bigint,
    is_manual_override boolean DEFAULT false NOT NULL,
    override_actor_type character varying(50),
    override_actor_key character varying(255),
    override_reason text,
    evidence jsonb DEFAULT '{}'::jsonb NOT NULL,
    is_active boolean DEFAULT true NOT NULL,
    superseded_at timestamp with time zone,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL,
    document_id bigint NOT NULL,
    entity_id bigint NOT NULL,
    mention_text text,
    entity_role character varying(50) DEFAULT 'mentioned'::character varying NOT NULL,
    CONSTRAINT ck_document_entities_confidence_range CHECK (((confidence >= (0)::numeric) AND (confidence <= (1)::numeric))),
    CONSTRAINT ck_document_entities_manual_override_actor CHECK (((NOT is_manual_override) OR ((override_actor_type IS NOT NULL) AND (override_actor_key IS NOT NULL)))),
    CONSTRAINT ck_document_entities_manual_override_method CHECK (((NOT is_manual_override) OR ((classification_method)::text = 'manual'::text)))
);


ALTER TABLE public.document_entities OWNER TO news_intelligence_app;

--
-- Name: document_entities_id_seq; Type: SEQUENCE; Schema: public; Owner: news_intelligence_app
--

CREATE SEQUENCE public.document_entities_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.document_entities_id_seq OWNER TO news_intelligence_app;

--
-- Name: document_entities_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: news_intelligence_app
--

ALTER SEQUENCE public.document_entities_id_seq OWNED BY public.document_entities.id;


--
-- Name: document_geographies; Type: TABLE; Schema: public; Owner: news_intelligence_app
--

CREATE TABLE public.document_geographies (
    id bigint NOT NULL,
    confidence numeric(5,4) NOT NULL,
    classification_method character varying(50) NOT NULL,
    classifier_version character varying(255),
    classification_run_id bigint,
    is_manual_override boolean DEFAULT false NOT NULL,
    override_actor_type character varying(50),
    override_actor_key character varying(255),
    override_reason text,
    evidence jsonb DEFAULT '{}'::jsonb NOT NULL,
    is_active boolean DEFAULT true NOT NULL,
    superseded_at timestamp with time zone,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL,
    document_id bigint NOT NULL,
    geography_id bigint NOT NULL,
    relationship_role character varying(50) NOT NULL,
    taxonomy_version character varying(50) NOT NULL,
    CONSTRAINT ck_document_geographies_confidence_range CHECK (((confidence >= (0)::numeric) AND (confidence <= (1)::numeric))),
    CONSTRAINT ck_document_geographies_manual_override_actor CHECK (((NOT is_manual_override) OR ((override_actor_type IS NOT NULL) AND (override_actor_key IS NOT NULL)))),
    CONSTRAINT ck_document_geographies_manual_override_method CHECK (((NOT is_manual_override) OR ((classification_method)::text = 'manual'::text)))
);


ALTER TABLE public.document_geographies OWNER TO news_intelligence_app;

--
-- Name: document_geographies_id_seq; Type: SEQUENCE; Schema: public; Owner: news_intelligence_app
--

CREATE SEQUENCE public.document_geographies_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.document_geographies_id_seq OWNER TO news_intelligence_app;

--
-- Name: document_geographies_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: news_intelligence_app
--

ALTER SEQUENCE public.document_geographies_id_seq OWNED BY public.document_geographies.id;


--
-- Name: document_topics; Type: TABLE; Schema: public; Owner: news_intelligence_app
--

CREATE TABLE public.document_topics (
    id bigint NOT NULL,
    confidence numeric(5,4) NOT NULL,
    classification_method character varying(50) NOT NULL,
    classifier_version character varying(255),
    classification_run_id bigint,
    is_manual_override boolean DEFAULT false NOT NULL,
    override_actor_type character varying(50),
    override_actor_key character varying(255),
    override_reason text,
    evidence jsonb DEFAULT '{}'::jsonb NOT NULL,
    is_active boolean DEFAULT true NOT NULL,
    superseded_at timestamp with time zone,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL,
    document_id bigint NOT NULL,
    topic_id bigint NOT NULL,
    relationship_role character varying(50) NOT NULL,
    taxonomy_version character varying(50) NOT NULL,
    CONSTRAINT ck_document_topics_confidence_range CHECK (((confidence >= (0)::numeric) AND (confidence <= (1)::numeric))),
    CONSTRAINT ck_document_topics_manual_override_actor CHECK (((NOT is_manual_override) OR ((override_actor_type IS NOT NULL) AND (override_actor_key IS NOT NULL)))),
    CONSTRAINT ck_document_topics_manual_override_method CHECK (((NOT is_manual_override) OR ((classification_method)::text = 'manual'::text)))
);


ALTER TABLE public.document_topics OWNER TO news_intelligence_app;

--
-- Name: document_topics_id_seq; Type: SEQUENCE; Schema: public; Owner: news_intelligence_app
--

CREATE SEQUENCE public.document_topics_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.document_topics_id_seq OWNER TO news_intelligence_app;

--
-- Name: document_topics_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: news_intelligence_app
--

ALTER SEQUENCE public.document_topics_id_seq OWNED BY public.document_topics.id;


--
-- Name: document_type_assignments; Type: TABLE; Schema: public; Owner: news_intelligence_app
--

CREATE TABLE public.document_type_assignments (
    id bigint NOT NULL,
    confidence numeric(5,4) NOT NULL,
    classification_method character varying(50) NOT NULL,
    classifier_version character varying(255),
    classification_run_id bigint,
    is_manual_override boolean DEFAULT false NOT NULL,
    override_actor_type character varying(50),
    override_actor_key character varying(255),
    override_reason text,
    evidence jsonb DEFAULT '{}'::jsonb NOT NULL,
    is_active boolean DEFAULT true NOT NULL,
    superseded_at timestamp with time zone,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL,
    document_id bigint NOT NULL,
    document_type_id bigint NOT NULL,
    is_primary boolean DEFAULT false NOT NULL,
    CONSTRAINT ck_document_type_assignments_confidence_range CHECK (((confidence >= (0)::numeric) AND (confidence <= (1)::numeric))),
    CONSTRAINT ck_document_type_assignments_manual_override_actor CHECK (((NOT is_manual_override) OR ((override_actor_type IS NOT NULL) AND (override_actor_key IS NOT NULL)))),
    CONSTRAINT ck_document_type_assignments_manual_override_method CHECK (((NOT is_manual_override) OR ((classification_method)::text = 'manual'::text)))
);


ALTER TABLE public.document_type_assignments OWNER TO news_intelligence_app;

--
-- Name: document_type_assignments_id_seq; Type: SEQUENCE; Schema: public; Owner: news_intelligence_app
--

CREATE SEQUENCE public.document_type_assignments_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.document_type_assignments_id_seq OWNER TO news_intelligence_app;

--
-- Name: document_type_assignments_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: news_intelligence_app
--

ALTER SEQUENCE public.document_type_assignments_id_seq OWNED BY public.document_type_assignments.id;


--
-- Name: document_types; Type: TABLE; Schema: public; Owner: news_intelligence_app
--

CREATE TABLE public.document_types (
    id bigint NOT NULL,
    parent_id bigint,
    slug character varying(255) NOT NULL,
    name character varying(255) NOT NULL,
    description text,
    is_active boolean DEFAULT true NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL
);


ALTER TABLE public.document_types OWNER TO news_intelligence_app;

--
-- Name: document_types_id_seq; Type: SEQUENCE; Schema: public; Owner: news_intelligence_app
--

CREATE SEQUENCE public.document_types_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.document_types_id_seq OWNER TO news_intelligence_app;

--
-- Name: document_types_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: news_intelligence_app
--

ALTER SEQUENCE public.document_types_id_seq OWNED BY public.document_types.id;


--
-- Name: document_versions; Type: TABLE; Schema: public; Owner: news_intelligence_app
--

CREATE TABLE public.document_versions (
    id bigint NOT NULL,
    document_id bigint NOT NULL,
    version_number integer NOT NULL,
    canonical_url text,
    title_original text NOT NULL,
    summary_original text,
    content_original text,
    language character varying(20),
    country character varying(100),
    author character varying(512),
    published_at timestamp with time zone,
    source_updated_at timestamp with time zone,
    retrieved_at timestamp with time zone NOT NULL,
    content_hash character varying(64) NOT NULL,
    changed_fields jsonb DEFAULT '[]'::jsonb NOT NULL,
    metadata jsonb DEFAULT '{}'::jsonb NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    CONSTRAINT ck_document_versions_version_number_positive CHECK ((version_number >= 1))
);


ALTER TABLE public.document_versions OWNER TO news_intelligence_app;

--
-- Name: document_versions_id_seq; Type: SEQUENCE; Schema: public; Owner: news_intelligence_app
--

CREATE SEQUENCE public.document_versions_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.document_versions_id_seq OWNER TO news_intelligence_app;

--
-- Name: document_versions_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: news_intelligence_app
--

ALTER SEQUENCE public.document_versions_id_seq OWNED BY public.document_versions.id;


--
-- Name: documents; Type: TABLE; Schema: public; Owner: news_intelligence_app
--

CREATE TABLE public.documents (
    id bigint NOT NULL,
    source_id bigint NOT NULL,
    source_endpoint_id bigint,
    source_type character varying(30) DEFAULT 'rss'::character varying NOT NULL,
    external_id character varying(2048),
    canonical_url text,
    title_original text NOT NULL,
    summary_original text,
    content_original text,
    language character varying(20),
    country character varying(100),
    author character varying(512),
    published_at timestamp with time zone,
    source_updated_at timestamp with time zone,
    retrieved_at timestamp with time zone DEFAULT now() NOT NULL,
    content_hash character varying(64) NOT NULL,
    metadata jsonb DEFAULT '{}'::jsonb NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL
);


ALTER TABLE public.documents OWNER TO news_intelligence_app;

--
-- Name: documents_id_seq; Type: SEQUENCE; Schema: public; Owner: news_intelligence_app
--

CREATE SEQUENCE public.documents_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.documents_id_seq OWNER TO news_intelligence_app;

--
-- Name: documents_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: news_intelligence_app
--

ALTER SEQUENCE public.documents_id_seq OWNED BY public.documents.id;


--
-- Name: entities; Type: TABLE; Schema: public; Owner: news_intelligence_app
--

CREATE TABLE public.entities (
    id bigint NOT NULL,
    entity_type character varying(50) NOT NULL,
    canonical_name character varying(512) NOT NULL,
    canonical_name_native character varying(512),
    country_or_jurisdiction character varying(255),
    is_active boolean DEFAULT true NOT NULL,
    metadata jsonb DEFAULT '{}'::jsonb NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL
);


ALTER TABLE public.entities OWNER TO news_intelligence_app;

--
-- Name: entities_id_seq; Type: SEQUENCE; Schema: public; Owner: news_intelligence_app
--

CREATE SEQUENCE public.entities_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.entities_id_seq OWNER TO news_intelligence_app;

--
-- Name: entities_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: news_intelligence_app
--

ALTER SEQUENCE public.entities_id_seq OWNED BY public.entities.id;


--
-- Name: entity_aliases; Type: TABLE; Schema: public; Owner: news_intelligence_app
--

CREATE TABLE public.entity_aliases (
    id bigint NOT NULL,
    entity_id bigint NOT NULL,
    alias character varying(512) NOT NULL,
    language character varying(20) DEFAULT 'und'::character varying NOT NULL,
    script character varying(50),
    alias_type character varying(50),
    is_preferred boolean DEFAULT false NOT NULL,
    normalized_alias character varying(512) NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL
);


ALTER TABLE public.entity_aliases OWNER TO news_intelligence_app;

--
-- Name: entity_aliases_id_seq; Type: SEQUENCE; Schema: public; Owner: news_intelligence_app
--

CREATE SEQUENCE public.entity_aliases_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.entity_aliases_id_seq OWNER TO news_intelligence_app;

--
-- Name: entity_aliases_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: news_intelligence_app
--

ALTER SEQUENCE public.entity_aliases_id_seq OWNED BY public.entity_aliases.id;


--
-- Name: geographies; Type: TABLE; Schema: public; Owner: news_intelligence_app
--

CREATE TABLE public.geographies (
    id bigint NOT NULL,
    parent_id bigint,
    slug character varying(255) NOT NULL,
    name character varying(255) NOT NULL,
    native_name character varying(255),
    geography_type character varying(50) NOT NULL,
    iso_code character varying(20),
    country_code character varying(10),
    region_code character varying(50),
    is_active boolean DEFAULT true NOT NULL,
    metadata jsonb DEFAULT '{}'::jsonb NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL
);


ALTER TABLE public.geographies OWNER TO news_intelligence_app;

--
-- Name: geographies_id_seq; Type: SEQUENCE; Schema: public; Owner: news_intelligence_app
--

CREATE SEQUENCE public.geographies_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.geographies_id_seq OWNER TO news_intelligence_app;

--
-- Name: geographies_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: news_intelligence_app
--

ALTER SEQUENCE public.geographies_id_seq OWNED BY public.geographies.id;


--
-- Name: ingestion_runs; Type: TABLE; Schema: public; Owner: news_intelligence_app
--

CREATE TABLE public.ingestion_runs (
    id bigint NOT NULL,
    source_id bigint NOT NULL,
    source_endpoint_id bigint,
    endpoint_url text NOT NULL,
    trigger_type character varying(30) DEFAULT 'scheduled'::character varying NOT NULL,
    status character varying(30) DEFAULT 'running'::character varying NOT NULL,
    started_at timestamp with time zone DEFAULT now() NOT NULL,
    finished_at timestamp with time zone,
    duration_ms bigint,
    http_status integer,
    response_bytes bigint,
    items_seen integer DEFAULT 0 NOT NULL,
    items_created integer DEFAULT 0 NOT NULL,
    items_updated integer DEFAULT 0 NOT NULL,
    items_unchanged integer DEFAULT 0 NOT NULL,
    items_failed integer DEFAULT 0 NOT NULL,
    error_type character varying(255),
    error_message text,
    error_details jsonb DEFAULT '{}'::jsonb NOT NULL,
    metadata jsonb DEFAULT '{}'::jsonb NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL,
    CONSTRAINT ck_ingestion_runs_duration_nonnegative CHECK (((duration_ms IS NULL) OR (duration_ms >= 0))),
    CONSTRAINT ck_ingestion_runs_finished_after_started CHECK (((finished_at IS NULL) OR (finished_at >= started_at))),
    CONSTRAINT ck_ingestion_runs_http_status_valid CHECK (((http_status IS NULL) OR ((http_status >= 100) AND (http_status <= 599)))),
    CONSTRAINT ck_ingestion_runs_item_counts_nonnegative CHECK (((items_seen >= 0) AND (items_created >= 0) AND (items_updated >= 0) AND (items_unchanged >= 0) AND (items_failed >= 0))),
    CONSTRAINT ck_ingestion_runs_response_bytes_nonnegative CHECK (((response_bytes IS NULL) OR (response_bytes >= 0)))
);


ALTER TABLE public.ingestion_runs OWNER TO news_intelligence_app;

--
-- Name: ingestion_runs_id_seq; Type: SEQUENCE; Schema: public; Owner: news_intelligence_app
--

CREATE SEQUENCE public.ingestion_runs_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.ingestion_runs_id_seq OWNER TO news_intelligence_app;

--
-- Name: ingestion_runs_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: news_intelligence_app
--

ALTER SEQUENCE public.ingestion_runs_id_seq OWNED BY public.ingestion_runs.id;


--
-- Name: source_endpoints; Type: TABLE; Schema: public; Owner: news_intelligence_app
--

CREATE TABLE public.source_endpoints (
    id bigint NOT NULL,
    source_id bigint NOT NULL,
    name character varying(255),
    endpoint_type character varying(30) DEFAULT 'rss'::character varying NOT NULL,
    url text NOT NULL,
    status character varying(30) DEFAULT 'active'::character varying NOT NULL,
    poll_interval_seconds integer DEFAULT 900 NOT NULL,
    last_checked_at timestamp with time zone,
    last_success_at timestamp with time zone,
    next_poll_at timestamp with time zone,
    etag character varying(512),
    last_modified character varying(255),
    last_http_status integer,
    consecutive_failures integer DEFAULT 0 NOT NULL,
    last_error text,
    metadata jsonb DEFAULT '{}'::jsonb NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL,
    CONSTRAINT ck_source_endpoints_poll_interval_minimum CHECK ((poll_interval_seconds >= 60))
);


ALTER TABLE public.source_endpoints OWNER TO news_intelligence_app;

--
-- Name: source_endpoints_id_seq; Type: SEQUENCE; Schema: public; Owner: news_intelligence_app
--

CREATE SEQUENCE public.source_endpoints_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.source_endpoints_id_seq OWNER TO news_intelligence_app;

--
-- Name: source_endpoints_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: news_intelligence_app
--

ALTER SEQUENCE public.source_endpoints_id_seq OWNED BY public.source_endpoints.id;


--
-- Name: sources; Type: TABLE; Schema: public; Owner: news_intelligence_app
--

CREATE TABLE public.sources (
    id bigint NOT NULL,
    name character varying(255) NOT NULL,
    native_name character varying(255),
    country character varying(100) NOT NULL,
    primary_language character varying(20) NOT NULL,
    source_type character varying(50) NOT NULL,
    status character varying(30) DEFAULT 'active'::character varying NOT NULL,
    priority character varying(20) DEFAULT 'normal'::character varying NOT NULL,
    website_url text,
    metadata jsonb DEFAULT '{}'::jsonb NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL
);


ALTER TABLE public.sources OWNER TO news_intelligence_app;

--
-- Name: sources_id_seq; Type: SEQUENCE; Schema: public; Owner: news_intelligence_app
--

CREATE SEQUENCE public.sources_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.sources_id_seq OWNER TO news_intelligence_app;

--
-- Name: sources_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: news_intelligence_app
--

ALTER SEQUENCE public.sources_id_seq OWNED BY public.sources.id;


--
-- Name: topics; Type: TABLE; Schema: public; Owner: news_intelligence_app
--

CREATE TABLE public.topics (
    id bigint NOT NULL,
    parent_id bigint,
    slug character varying(255) NOT NULL,
    name character varying(255) NOT NULL,
    native_name character varying(255),
    description text,
    depth integer DEFAULT 0 NOT NULL,
    sort_order integer DEFAULT 0 NOT NULL,
    taxonomy_version character varying(50) NOT NULL,
    is_active boolean DEFAULT true NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL,
    CONSTRAINT ck_topics_depth_nonnegative CHECK ((depth >= 0)),
    CONSTRAINT ck_topics_sort_order_nonnegative CHECK ((sort_order >= 0))
);


ALTER TABLE public.topics OWNER TO news_intelligence_app;

--
-- Name: topics_id_seq; Type: SEQUENCE; Schema: public; Owner: news_intelligence_app
--

CREATE SEQUENCE public.topics_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.topics_id_seq OWNER TO news_intelligence_app;

--
-- Name: topics_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: news_intelligence_app
--

ALTER SEQUENCE public.topics_id_seq OWNED BY public.topics.id;


--
-- Name: classification_runs id; Type: DEFAULT; Schema: public; Owner: news_intelligence_app
--

ALTER TABLE ONLY public.classification_runs ALTER COLUMN id SET DEFAULT nextval('public.classification_runs_id_seq'::regclass);


--
-- Name: document_entities id; Type: DEFAULT; Schema: public; Owner: news_intelligence_app
--

ALTER TABLE ONLY public.document_entities ALTER COLUMN id SET DEFAULT nextval('public.document_entities_id_seq'::regclass);


--
-- Name: document_geographies id; Type: DEFAULT; Schema: public; Owner: news_intelligence_app
--

ALTER TABLE ONLY public.document_geographies ALTER COLUMN id SET DEFAULT nextval('public.document_geographies_id_seq'::regclass);


--
-- Name: document_topics id; Type: DEFAULT; Schema: public; Owner: news_intelligence_app
--

ALTER TABLE ONLY public.document_topics ALTER COLUMN id SET DEFAULT nextval('public.document_topics_id_seq'::regclass);


--
-- Name: document_type_assignments id; Type: DEFAULT; Schema: public; Owner: news_intelligence_app
--

ALTER TABLE ONLY public.document_type_assignments ALTER COLUMN id SET DEFAULT nextval('public.document_type_assignments_id_seq'::regclass);


--
-- Name: document_types id; Type: DEFAULT; Schema: public; Owner: news_intelligence_app
--

ALTER TABLE ONLY public.document_types ALTER COLUMN id SET DEFAULT nextval('public.document_types_id_seq'::regclass);


--
-- Name: document_versions id; Type: DEFAULT; Schema: public; Owner: news_intelligence_app
--

ALTER TABLE ONLY public.document_versions ALTER COLUMN id SET DEFAULT nextval('public.document_versions_id_seq'::regclass);


--
-- Name: documents id; Type: DEFAULT; Schema: public; Owner: news_intelligence_app
--

ALTER TABLE ONLY public.documents ALTER COLUMN id SET DEFAULT nextval('public.documents_id_seq'::regclass);


--
-- Name: entities id; Type: DEFAULT; Schema: public; Owner: news_intelligence_app
--

ALTER TABLE ONLY public.entities ALTER COLUMN id SET DEFAULT nextval('public.entities_id_seq'::regclass);


--
-- Name: entity_aliases id; Type: DEFAULT; Schema: public; Owner: news_intelligence_app
--

ALTER TABLE ONLY public.entity_aliases ALTER COLUMN id SET DEFAULT nextval('public.entity_aliases_id_seq'::regclass);


--
-- Name: geographies id; Type: DEFAULT; Schema: public; Owner: news_intelligence_app
--

ALTER TABLE ONLY public.geographies ALTER COLUMN id SET DEFAULT nextval('public.geographies_id_seq'::regclass);


--
-- Name: ingestion_runs id; Type: DEFAULT; Schema: public; Owner: news_intelligence_app
--

ALTER TABLE ONLY public.ingestion_runs ALTER COLUMN id SET DEFAULT nextval('public.ingestion_runs_id_seq'::regclass);


--
-- Name: source_endpoints id; Type: DEFAULT; Schema: public; Owner: news_intelligence_app
--

ALTER TABLE ONLY public.source_endpoints ALTER COLUMN id SET DEFAULT nextval('public.source_endpoints_id_seq'::regclass);


--
-- Name: sources id; Type: DEFAULT; Schema: public; Owner: news_intelligence_app
--

ALTER TABLE ONLY public.sources ALTER COLUMN id SET DEFAULT nextval('public.sources_id_seq'::regclass);


--
-- Name: topics id; Type: DEFAULT; Schema: public; Owner: news_intelligence_app
--

ALTER TABLE ONLY public.topics ALTER COLUMN id SET DEFAULT nextval('public.topics_id_seq'::regclass);


--
-- Name: alembic_version alembic_version_pkc; Type: CONSTRAINT; Schema: public; Owner: news_intelligence_app
--

ALTER TABLE ONLY public.alembic_version
    ADD CONSTRAINT alembic_version_pkc PRIMARY KEY (version_num);


--
-- Name: classification_runs pk_classification_runs; Type: CONSTRAINT; Schema: public; Owner: news_intelligence_app
--

ALTER TABLE ONLY public.classification_runs
    ADD CONSTRAINT pk_classification_runs PRIMARY KEY (id);


--
-- Name: document_entities pk_document_entities; Type: CONSTRAINT; Schema: public; Owner: news_intelligence_app
--

ALTER TABLE ONLY public.document_entities
    ADD CONSTRAINT pk_document_entities PRIMARY KEY (id);


--
-- Name: document_geographies pk_document_geographies; Type: CONSTRAINT; Schema: public; Owner: news_intelligence_app
--

ALTER TABLE ONLY public.document_geographies
    ADD CONSTRAINT pk_document_geographies PRIMARY KEY (id);


--
-- Name: document_topics pk_document_topics; Type: CONSTRAINT; Schema: public; Owner: news_intelligence_app
--

ALTER TABLE ONLY public.document_topics
    ADD CONSTRAINT pk_document_topics PRIMARY KEY (id);


--
-- Name: document_type_assignments pk_document_type_assignments; Type: CONSTRAINT; Schema: public; Owner: news_intelligence_app
--

ALTER TABLE ONLY public.document_type_assignments
    ADD CONSTRAINT pk_document_type_assignments PRIMARY KEY (id);


--
-- Name: document_types pk_document_types; Type: CONSTRAINT; Schema: public; Owner: news_intelligence_app
--

ALTER TABLE ONLY public.document_types
    ADD CONSTRAINT pk_document_types PRIMARY KEY (id);


--
-- Name: document_versions pk_document_versions; Type: CONSTRAINT; Schema: public; Owner: news_intelligence_app
--

ALTER TABLE ONLY public.document_versions
    ADD CONSTRAINT pk_document_versions PRIMARY KEY (id);


--
-- Name: documents pk_documents; Type: CONSTRAINT; Schema: public; Owner: news_intelligence_app
--

ALTER TABLE ONLY public.documents
    ADD CONSTRAINT pk_documents PRIMARY KEY (id);


--
-- Name: entities pk_entities; Type: CONSTRAINT; Schema: public; Owner: news_intelligence_app
--

ALTER TABLE ONLY public.entities
    ADD CONSTRAINT pk_entities PRIMARY KEY (id);


--
-- Name: entity_aliases pk_entity_aliases; Type: CONSTRAINT; Schema: public; Owner: news_intelligence_app
--

ALTER TABLE ONLY public.entity_aliases
    ADD CONSTRAINT pk_entity_aliases PRIMARY KEY (id);


--
-- Name: geographies pk_geographies; Type: CONSTRAINT; Schema: public; Owner: news_intelligence_app
--

ALTER TABLE ONLY public.geographies
    ADD CONSTRAINT pk_geographies PRIMARY KEY (id);


--
-- Name: ingestion_runs pk_ingestion_runs; Type: CONSTRAINT; Schema: public; Owner: news_intelligence_app
--

ALTER TABLE ONLY public.ingestion_runs
    ADD CONSTRAINT pk_ingestion_runs PRIMARY KEY (id);


--
-- Name: source_endpoints pk_source_endpoints; Type: CONSTRAINT; Schema: public; Owner: news_intelligence_app
--

ALTER TABLE ONLY public.source_endpoints
    ADD CONSTRAINT pk_source_endpoints PRIMARY KEY (id);


--
-- Name: sources pk_sources; Type: CONSTRAINT; Schema: public; Owner: news_intelligence_app
--

ALTER TABLE ONLY public.sources
    ADD CONSTRAINT pk_sources PRIMARY KEY (id);


--
-- Name: topics pk_topics; Type: CONSTRAINT; Schema: public; Owner: news_intelligence_app
--

ALTER TABLE ONLY public.topics
    ADD CONSTRAINT pk_topics PRIMARY KEY (id);


--
-- Name: document_types uq_document_types_slug; Type: CONSTRAINT; Schema: public; Owner: news_intelligence_app
--

ALTER TABLE ONLY public.document_types
    ADD CONSTRAINT uq_document_types_slug UNIQUE (slug);


--
-- Name: document_versions uq_document_versions_document_hash; Type: CONSTRAINT; Schema: public; Owner: news_intelligence_app
--

ALTER TABLE ONLY public.document_versions
    ADD CONSTRAINT uq_document_versions_document_hash UNIQUE (document_id, content_hash);


--
-- Name: document_versions uq_document_versions_document_version; Type: CONSTRAINT; Schema: public; Owner: news_intelligence_app
--

ALTER TABLE ONLY public.document_versions
    ADD CONSTRAINT uq_document_versions_document_version UNIQUE (document_id, version_number);


--
-- Name: documents uq_documents_endpoint_external_id; Type: CONSTRAINT; Schema: public; Owner: news_intelligence_app
--

ALTER TABLE ONLY public.documents
    ADD CONSTRAINT uq_documents_endpoint_external_id UNIQUE (source_endpoint_id, external_id);


--
-- Name: entity_aliases uq_entity_aliases_entity_normalized_language; Type: CONSTRAINT; Schema: public; Owner: news_intelligence_app
--

ALTER TABLE ONLY public.entity_aliases
    ADD CONSTRAINT uq_entity_aliases_entity_normalized_language UNIQUE (entity_id, normalized_alias, language);


--
-- Name: geographies uq_geographies_slug; Type: CONSTRAINT; Schema: public; Owner: news_intelligence_app
--

ALTER TABLE ONLY public.geographies
    ADD CONSTRAINT uq_geographies_slug UNIQUE (slug);


--
-- Name: source_endpoints uq_source_endpoints_url; Type: CONSTRAINT; Schema: public; Owner: news_intelligence_app
--

ALTER TABLE ONLY public.source_endpoints
    ADD CONSTRAINT uq_source_endpoints_url UNIQUE (url);


--
-- Name: sources uq_sources_website_url; Type: CONSTRAINT; Schema: public; Owner: news_intelligence_app
--

ALTER TABLE ONLY public.sources
    ADD CONSTRAINT uq_sources_website_url UNIQUE (website_url);


--
-- Name: topics uq_topics_slug; Type: CONSTRAINT; Schema: public; Owner: news_intelligence_app
--

ALTER TABLE ONLY public.topics
    ADD CONSTRAINT uq_topics_slug UNIQUE (slug);


--
-- Name: ix_classification_runs_document_started; Type: INDEX; Schema: public; Owner: news_intelligence_app
--

CREATE INDEX ix_classification_runs_document_started ON public.classification_runs USING btree (document_id, started_at);


--
-- Name: ix_classification_runs_status_started; Type: INDEX; Schema: public; Owner: news_intelligence_app
--

CREATE INDEX ix_classification_runs_status_started ON public.classification_runs USING btree (status, started_at);


--
-- Name: ix_document_entities_classification_run; Type: INDEX; Schema: public; Owner: news_intelligence_app
--

CREATE INDEX ix_document_entities_classification_run ON public.document_entities USING btree (classification_run_id);


--
-- Name: ix_document_entities_document_active; Type: INDEX; Schema: public; Owner: news_intelligence_app
--

CREATE INDEX ix_document_entities_document_active ON public.document_entities USING btree (document_id, is_active);


--
-- Name: ix_document_entities_entity_active; Type: INDEX; Schema: public; Owner: news_intelligence_app
--

CREATE INDEX ix_document_entities_entity_active ON public.document_entities USING btree (entity_id, is_active);


--
-- Name: ix_document_geographies_classification_run; Type: INDEX; Schema: public; Owner: news_intelligence_app
--

CREATE INDEX ix_document_geographies_classification_run ON public.document_geographies USING btree (classification_run_id);


--
-- Name: ix_document_geographies_document_active; Type: INDEX; Schema: public; Owner: news_intelligence_app
--

CREATE INDEX ix_document_geographies_document_active ON public.document_geographies USING btree (document_id, is_active);


--
-- Name: ix_document_geographies_geography_active; Type: INDEX; Schema: public; Owner: news_intelligence_app
--

CREATE INDEX ix_document_geographies_geography_active ON public.document_geographies USING btree (geography_id, is_active);


--
-- Name: ix_document_topics_classification_run; Type: INDEX; Schema: public; Owner: news_intelligence_app
--

CREATE INDEX ix_document_topics_classification_run ON public.document_topics USING btree (classification_run_id);


--
-- Name: ix_document_topics_document_active; Type: INDEX; Schema: public; Owner: news_intelligence_app
--

CREATE INDEX ix_document_topics_document_active ON public.document_topics USING btree (document_id, is_active);


--
-- Name: ix_document_topics_topic_active; Type: INDEX; Schema: public; Owner: news_intelligence_app
--

CREATE INDEX ix_document_topics_topic_active ON public.document_topics USING btree (topic_id, is_active);


--
-- Name: ix_document_type_assignments_classification_run; Type: INDEX; Schema: public; Owner: news_intelligence_app
--

CREATE INDEX ix_document_type_assignments_classification_run ON public.document_type_assignments USING btree (classification_run_id);


--
-- Name: ix_document_type_assignments_document_active; Type: INDEX; Schema: public; Owner: news_intelligence_app
--

CREATE INDEX ix_document_type_assignments_document_active ON public.document_type_assignments USING btree (document_id, is_active);


--
-- Name: ix_document_type_assignments_document_type_active; Type: INDEX; Schema: public; Owner: news_intelligence_app
--

CREATE INDEX ix_document_type_assignments_document_type_active ON public.document_type_assignments USING btree (document_type_id, is_active);


--
-- Name: ix_document_types_active_name; Type: INDEX; Schema: public; Owner: news_intelligence_app
--

CREATE INDEX ix_document_types_active_name ON public.document_types USING btree (is_active, name);


--
-- Name: ix_document_types_parent_name; Type: INDEX; Schema: public; Owner: news_intelligence_app
--

CREATE INDEX ix_document_types_parent_name ON public.document_types USING btree (parent_id, name);


--
-- Name: ix_document_versions_content_hash; Type: INDEX; Schema: public; Owner: news_intelligence_app
--

CREATE INDEX ix_document_versions_content_hash ON public.document_versions USING btree (content_hash);


--
-- Name: ix_document_versions_document_created_at; Type: INDEX; Schema: public; Owner: news_intelligence_app
--

CREATE INDEX ix_document_versions_document_created_at ON public.document_versions USING btree (document_id, created_at);


--
-- Name: ix_document_versions_document_id; Type: INDEX; Schema: public; Owner: news_intelligence_app
--

CREATE INDEX ix_document_versions_document_id ON public.document_versions USING btree (document_id);


--
-- Name: ix_documents_content_hash; Type: INDEX; Schema: public; Owner: news_intelligence_app
--

CREATE INDEX ix_documents_content_hash ON public.documents USING btree (content_hash);


--
-- Name: ix_documents_country; Type: INDEX; Schema: public; Owner: news_intelligence_app
--

CREATE INDEX ix_documents_country ON public.documents USING btree (country);


--
-- Name: ix_documents_endpoint_published_at; Type: INDEX; Schema: public; Owner: news_intelligence_app
--

CREATE INDEX ix_documents_endpoint_published_at ON public.documents USING btree (source_endpoint_id, published_at);


--
-- Name: ix_documents_language; Type: INDEX; Schema: public; Owner: news_intelligence_app
--

CREATE INDEX ix_documents_language ON public.documents USING btree (language);


--
-- Name: ix_documents_published_at; Type: INDEX; Schema: public; Owner: news_intelligence_app
--

CREATE INDEX ix_documents_published_at ON public.documents USING btree (published_at);


--
-- Name: ix_documents_retrieved_at; Type: INDEX; Schema: public; Owner: news_intelligence_app
--

CREATE INDEX ix_documents_retrieved_at ON public.documents USING btree (retrieved_at);


--
-- Name: ix_documents_source_endpoint_id; Type: INDEX; Schema: public; Owner: news_intelligence_app
--

CREATE INDEX ix_documents_source_endpoint_id ON public.documents USING btree (source_endpoint_id);


--
-- Name: ix_documents_source_id; Type: INDEX; Schema: public; Owner: news_intelligence_app
--

CREATE INDEX ix_documents_source_id ON public.documents USING btree (source_id);


--
-- Name: ix_documents_source_published_at; Type: INDEX; Schema: public; Owner: news_intelligence_app
--

CREATE INDEX ix_documents_source_published_at ON public.documents USING btree (source_id, published_at);


--
-- Name: ix_documents_source_type; Type: INDEX; Schema: public; Owner: news_intelligence_app
--

CREATE INDEX ix_documents_source_type ON public.documents USING btree (source_type);


--
-- Name: ix_documents_source_type_published_at; Type: INDEX; Schema: public; Owner: news_intelligence_app
--

CREATE INDEX ix_documents_source_type_published_at ON public.documents USING btree (source_type, published_at);


--
-- Name: ix_entities_canonical_name; Type: INDEX; Schema: public; Owner: news_intelligence_app
--

CREATE INDEX ix_entities_canonical_name ON public.entities USING btree (canonical_name);


--
-- Name: ix_entities_country_or_jurisdiction; Type: INDEX; Schema: public; Owner: news_intelligence_app
--

CREATE INDEX ix_entities_country_or_jurisdiction ON public.entities USING btree (country_or_jurisdiction);


--
-- Name: ix_entities_type_active; Type: INDEX; Schema: public; Owner: news_intelligence_app
--

CREATE INDEX ix_entities_type_active ON public.entities USING btree (entity_type, is_active);


--
-- Name: ix_entity_aliases_normalized_language; Type: INDEX; Schema: public; Owner: news_intelligence_app
--

CREATE INDEX ix_entity_aliases_normalized_language ON public.entity_aliases USING btree (normalized_alias, language);


--
-- Name: ix_geographies_country_code; Type: INDEX; Schema: public; Owner: news_intelligence_app
--

CREATE INDEX ix_geographies_country_code ON public.geographies USING btree (country_code);


--
-- Name: ix_geographies_parent_name; Type: INDEX; Schema: public; Owner: news_intelligence_app
--

CREATE INDEX ix_geographies_parent_name ON public.geographies USING btree (parent_id, name);


--
-- Name: ix_geographies_region_code; Type: INDEX; Schema: public; Owner: news_intelligence_app
--

CREATE INDEX ix_geographies_region_code ON public.geographies USING btree (region_code);


--
-- Name: ix_geographies_type_active; Type: INDEX; Schema: public; Owner: news_intelligence_app
--

CREATE INDEX ix_geographies_type_active ON public.geographies USING btree (geography_type, is_active);


--
-- Name: ix_ingestion_runs_endpoint_started_at; Type: INDEX; Schema: public; Owner: news_intelligence_app
--

CREATE INDEX ix_ingestion_runs_endpoint_started_at ON public.ingestion_runs USING btree (source_endpoint_id, started_at);


--
-- Name: ix_ingestion_runs_source_started_at; Type: INDEX; Schema: public; Owner: news_intelligence_app
--

CREATE INDEX ix_ingestion_runs_source_started_at ON public.ingestion_runs USING btree (source_id, started_at);


--
-- Name: ix_ingestion_runs_status_started_at; Type: INDEX; Schema: public; Owner: news_intelligence_app
--

CREATE INDEX ix_ingestion_runs_status_started_at ON public.ingestion_runs USING btree (status, started_at);


--
-- Name: ix_source_endpoints_due_poll; Type: INDEX; Schema: public; Owner: news_intelligence_app
--

CREATE INDEX ix_source_endpoints_due_poll ON public.source_endpoints USING btree (status, next_poll_at);


--
-- Name: ix_source_endpoints_endpoint_type; Type: INDEX; Schema: public; Owner: news_intelligence_app
--

CREATE INDEX ix_source_endpoints_endpoint_type ON public.source_endpoints USING btree (endpoint_type);


--
-- Name: ix_source_endpoints_source_id; Type: INDEX; Schema: public; Owner: news_intelligence_app
--

CREATE INDEX ix_source_endpoints_source_id ON public.source_endpoints USING btree (source_id);


--
-- Name: ix_source_endpoints_source_status; Type: INDEX; Schema: public; Owner: news_intelligence_app
--

CREATE INDEX ix_source_endpoints_source_status ON public.source_endpoints USING btree (source_id, status);


--
-- Name: ix_source_endpoints_status; Type: INDEX; Schema: public; Owner: news_intelligence_app
--

CREATE INDEX ix_source_endpoints_status ON public.source_endpoints USING btree (status);


--
-- Name: ix_sources_country; Type: INDEX; Schema: public; Owner: news_intelligence_app
--

CREATE INDEX ix_sources_country ON public.sources USING btree (country);


--
-- Name: ix_sources_country_status; Type: INDEX; Schema: public; Owner: news_intelligence_app
--

CREATE INDEX ix_sources_country_status ON public.sources USING btree (country, status);


--
-- Name: ix_sources_priority; Type: INDEX; Schema: public; Owner: news_intelligence_app
--

CREATE INDEX ix_sources_priority ON public.sources USING btree (priority);


--
-- Name: ix_sources_source_type; Type: INDEX; Schema: public; Owner: news_intelligence_app
--

CREATE INDEX ix_sources_source_type ON public.sources USING btree (source_type);


--
-- Name: ix_sources_status; Type: INDEX; Schema: public; Owner: news_intelligence_app
--

CREATE INDEX ix_sources_status ON public.sources USING btree (status);


--
-- Name: ix_sources_type_status; Type: INDEX; Schema: public; Owner: news_intelligence_app
--

CREATE INDEX ix_sources_type_status ON public.sources USING btree (source_type, status);


--
-- Name: ix_topics_active_sort_order; Type: INDEX; Schema: public; Owner: news_intelligence_app
--

CREATE INDEX ix_topics_active_sort_order ON public.topics USING btree (is_active, sort_order);


--
-- Name: ix_topics_parent_sort_order; Type: INDEX; Schema: public; Owner: news_intelligence_app
--

CREATE INDEX ix_topics_parent_sort_order ON public.topics USING btree (parent_id, sort_order);


--
-- Name: uq_document_entities_active_relationship; Type: INDEX; Schema: public; Owner: news_intelligence_app
--

CREATE UNIQUE INDEX uq_document_entities_active_relationship ON public.document_entities USING btree (document_id, entity_id, entity_role) WHERE is_active;


--
-- Name: uq_document_geographies_active_relationship; Type: INDEX; Schema: public; Owner: news_intelligence_app
--

CREATE UNIQUE INDEX uq_document_geographies_active_relationship ON public.document_geographies USING btree (document_id, geography_id, relationship_role) WHERE is_active;


--
-- Name: uq_document_topics_active_relationship; Type: INDEX; Schema: public; Owner: news_intelligence_app
--

CREATE UNIQUE INDEX uq_document_topics_active_relationship ON public.document_topics USING btree (document_id, topic_id, relationship_role) WHERE is_active;


--
-- Name: uq_document_type_assignments_active_primary; Type: INDEX; Schema: public; Owner: news_intelligence_app
--

CREATE UNIQUE INDEX uq_document_type_assignments_active_primary ON public.document_type_assignments USING btree (document_id) WHERE (is_active AND is_primary);


--
-- Name: uq_document_type_assignments_active_type; Type: INDEX; Schema: public; Owner: news_intelligence_app
--

CREATE UNIQUE INDEX uq_document_type_assignments_active_type ON public.document_type_assignments USING btree (document_id, document_type_id) WHERE is_active;


--
-- Name: classification_runs fk_classification_runs_document_id_documents; Type: FK CONSTRAINT; Schema: public; Owner: news_intelligence_app
--

ALTER TABLE ONLY public.classification_runs
    ADD CONSTRAINT fk_classification_runs_document_id_documents FOREIGN KEY (document_id) REFERENCES public.documents(id) ON DELETE CASCADE;


--
-- Name: document_entities fk_document_entities_classification_run_id_classification_runs; Type: FK CONSTRAINT; Schema: public; Owner: news_intelligence_app
--

ALTER TABLE ONLY public.document_entities
    ADD CONSTRAINT fk_document_entities_classification_run_id_classification_runs FOREIGN KEY (classification_run_id) REFERENCES public.classification_runs(id) ON DELETE SET NULL;


--
-- Name: document_entities fk_document_entities_document_id_documents; Type: FK CONSTRAINT; Schema: public; Owner: news_intelligence_app
--

ALTER TABLE ONLY public.document_entities
    ADD CONSTRAINT fk_document_entities_document_id_documents FOREIGN KEY (document_id) REFERENCES public.documents(id) ON DELETE CASCADE;


--
-- Name: document_entities fk_document_entities_entity_id_entities; Type: FK CONSTRAINT; Schema: public; Owner: news_intelligence_app
--

ALTER TABLE ONLY public.document_entities
    ADD CONSTRAINT fk_document_entities_entity_id_entities FOREIGN KEY (entity_id) REFERENCES public.entities(id) ON DELETE RESTRICT;


--
-- Name: document_geographies fk_document_geographies_classification_run_id_classific_8c61; Type: FK CONSTRAINT; Schema: public; Owner: news_intelligence_app
--

ALTER TABLE ONLY public.document_geographies
    ADD CONSTRAINT fk_document_geographies_classification_run_id_classific_8c61 FOREIGN KEY (classification_run_id) REFERENCES public.classification_runs(id) ON DELETE SET NULL;


--
-- Name: document_geographies fk_document_geographies_document_id_documents; Type: FK CONSTRAINT; Schema: public; Owner: news_intelligence_app
--

ALTER TABLE ONLY public.document_geographies
    ADD CONSTRAINT fk_document_geographies_document_id_documents FOREIGN KEY (document_id) REFERENCES public.documents(id) ON DELETE CASCADE;


--
-- Name: document_geographies fk_document_geographies_geography_id_geographies; Type: FK CONSTRAINT; Schema: public; Owner: news_intelligence_app
--

ALTER TABLE ONLY public.document_geographies
    ADD CONSTRAINT fk_document_geographies_geography_id_geographies FOREIGN KEY (geography_id) REFERENCES public.geographies(id) ON DELETE RESTRICT;


--
-- Name: document_topics fk_document_topics_classification_run_id_classification_runs; Type: FK CONSTRAINT; Schema: public; Owner: news_intelligence_app
--

ALTER TABLE ONLY public.document_topics
    ADD CONSTRAINT fk_document_topics_classification_run_id_classification_runs FOREIGN KEY (classification_run_id) REFERENCES public.classification_runs(id) ON DELETE SET NULL;


--
-- Name: document_topics fk_document_topics_document_id_documents; Type: FK CONSTRAINT; Schema: public; Owner: news_intelligence_app
--

ALTER TABLE ONLY public.document_topics
    ADD CONSTRAINT fk_document_topics_document_id_documents FOREIGN KEY (document_id) REFERENCES public.documents(id) ON DELETE CASCADE;


--
-- Name: document_topics fk_document_topics_topic_id_topics; Type: FK CONSTRAINT; Schema: public; Owner: news_intelligence_app
--

ALTER TABLE ONLY public.document_topics
    ADD CONSTRAINT fk_document_topics_topic_id_topics FOREIGN KEY (topic_id) REFERENCES public.topics(id) ON DELETE RESTRICT;


--
-- Name: document_type_assignments fk_document_type_assignments_classification_run_id_clas_558d; Type: FK CONSTRAINT; Schema: public; Owner: news_intelligence_app
--

ALTER TABLE ONLY public.document_type_assignments
    ADD CONSTRAINT fk_document_type_assignments_classification_run_id_clas_558d FOREIGN KEY (classification_run_id) REFERENCES public.classification_runs(id) ON DELETE SET NULL;


--
-- Name: document_type_assignments fk_document_type_assignments_document_id_documents; Type: FK CONSTRAINT; Schema: public; Owner: news_intelligence_app
--

ALTER TABLE ONLY public.document_type_assignments
    ADD CONSTRAINT fk_document_type_assignments_document_id_documents FOREIGN KEY (document_id) REFERENCES public.documents(id) ON DELETE CASCADE;


--
-- Name: document_type_assignments fk_document_type_assignments_document_type_id_document_types; Type: FK CONSTRAINT; Schema: public; Owner: news_intelligence_app
--

ALTER TABLE ONLY public.document_type_assignments
    ADD CONSTRAINT fk_document_type_assignments_document_type_id_document_types FOREIGN KEY (document_type_id) REFERENCES public.document_types(id) ON DELETE RESTRICT;


--
-- Name: document_types fk_document_types_parent_id_document_types; Type: FK CONSTRAINT; Schema: public; Owner: news_intelligence_app
--

ALTER TABLE ONLY public.document_types
    ADD CONSTRAINT fk_document_types_parent_id_document_types FOREIGN KEY (parent_id) REFERENCES public.document_types(id) ON DELETE RESTRICT;


--
-- Name: document_versions fk_document_versions_document_id_documents; Type: FK CONSTRAINT; Schema: public; Owner: news_intelligence_app
--

ALTER TABLE ONLY public.document_versions
    ADD CONSTRAINT fk_document_versions_document_id_documents FOREIGN KEY (document_id) REFERENCES public.documents(id) ON DELETE CASCADE;


--
-- Name: documents fk_documents_source_endpoint_id_source_endpoints; Type: FK CONSTRAINT; Schema: public; Owner: news_intelligence_app
--

ALTER TABLE ONLY public.documents
    ADD CONSTRAINT fk_documents_source_endpoint_id_source_endpoints FOREIGN KEY (source_endpoint_id) REFERENCES public.source_endpoints(id) ON DELETE SET NULL;


--
-- Name: documents fk_documents_source_id_sources; Type: FK CONSTRAINT; Schema: public; Owner: news_intelligence_app
--

ALTER TABLE ONLY public.documents
    ADD CONSTRAINT fk_documents_source_id_sources FOREIGN KEY (source_id) REFERENCES public.sources(id) ON DELETE RESTRICT;


--
-- Name: entity_aliases fk_entity_aliases_entity_id_entities; Type: FK CONSTRAINT; Schema: public; Owner: news_intelligence_app
--

ALTER TABLE ONLY public.entity_aliases
    ADD CONSTRAINT fk_entity_aliases_entity_id_entities FOREIGN KEY (entity_id) REFERENCES public.entities(id) ON DELETE CASCADE;


--
-- Name: geographies fk_geographies_parent_id_geographies; Type: FK CONSTRAINT; Schema: public; Owner: news_intelligence_app
--

ALTER TABLE ONLY public.geographies
    ADD CONSTRAINT fk_geographies_parent_id_geographies FOREIGN KEY (parent_id) REFERENCES public.geographies(id) ON DELETE RESTRICT;


--
-- Name: ingestion_runs fk_ingestion_runs_source_endpoint_id_source_endpoints; Type: FK CONSTRAINT; Schema: public; Owner: news_intelligence_app
--

ALTER TABLE ONLY public.ingestion_runs
    ADD CONSTRAINT fk_ingestion_runs_source_endpoint_id_source_endpoints FOREIGN KEY (source_endpoint_id) REFERENCES public.source_endpoints(id) ON DELETE SET NULL;


--
-- Name: ingestion_runs fk_ingestion_runs_source_id_sources; Type: FK CONSTRAINT; Schema: public; Owner: news_intelligence_app
--

ALTER TABLE ONLY public.ingestion_runs
    ADD CONSTRAINT fk_ingestion_runs_source_id_sources FOREIGN KEY (source_id) REFERENCES public.sources(id) ON DELETE RESTRICT;


--
-- Name: source_endpoints fk_source_endpoints_source_id_sources; Type: FK CONSTRAINT; Schema: public; Owner: news_intelligence_app
--

ALTER TABLE ONLY public.source_endpoints
    ADD CONSTRAINT fk_source_endpoints_source_id_sources FOREIGN KEY (source_id) REFERENCES public.sources(id) ON DELETE CASCADE;


--
-- Name: topics fk_topics_parent_id_topics; Type: FK CONSTRAINT; Schema: public; Owner: news_intelligence_app
--

ALTER TABLE ONLY public.topics
    ADD CONSTRAINT fk_topics_parent_id_topics FOREIGN KEY (parent_id) REFERENCES public.topics(id) ON DELETE RESTRICT;


--
-- PostgreSQL database dump complete
--

\unrestrict 1Eg8aroonCWf9stJgpayKwlivgquL6tTAQh6mdIZqzWWIRlXFOMrWA2KbHUcVcf

