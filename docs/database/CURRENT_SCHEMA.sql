--
-- PostgreSQL database dump
--

\restrict 7ZdDcXgV2H6rC33DbWHn88yJuZFlAStaZPcaXsyBbjImSVKZcwMz0upyrFfwbPZ

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
-- Name: alembic_version; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.alembic_version (
    version_num character varying(32) NOT NULL
);


--
-- Name: document_versions; Type: TABLE; Schema: public; Owner: -
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


--
-- Name: document_versions_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.document_versions_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: document_versions_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.document_versions_id_seq OWNED BY public.document_versions.id;


--
-- Name: documents; Type: TABLE; Schema: public; Owner: -
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


--
-- Name: documents_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.documents_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: documents_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.documents_id_seq OWNED BY public.documents.id;


--
-- Name: ingestion_runs; Type: TABLE; Schema: public; Owner: -
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


--
-- Name: ingestion_runs_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.ingestion_runs_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: ingestion_runs_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.ingestion_runs_id_seq OWNED BY public.ingestion_runs.id;


--
-- Name: source_endpoints; Type: TABLE; Schema: public; Owner: -
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


--
-- Name: source_endpoints_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.source_endpoints_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: source_endpoints_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.source_endpoints_id_seq OWNED BY public.source_endpoints.id;


--
-- Name: sources; Type: TABLE; Schema: public; Owner: -
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


--
-- Name: sources_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.sources_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: sources_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.sources_id_seq OWNED BY public.sources.id;


--
-- Name: document_versions id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.document_versions ALTER COLUMN id SET DEFAULT nextval('public.document_versions_id_seq'::regclass);


--
-- Name: documents id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.documents ALTER COLUMN id SET DEFAULT nextval('public.documents_id_seq'::regclass);


--
-- Name: ingestion_runs id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.ingestion_runs ALTER COLUMN id SET DEFAULT nextval('public.ingestion_runs_id_seq'::regclass);


--
-- Name: source_endpoints id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.source_endpoints ALTER COLUMN id SET DEFAULT nextval('public.source_endpoints_id_seq'::regclass);


--
-- Name: sources id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.sources ALTER COLUMN id SET DEFAULT nextval('public.sources_id_seq'::regclass);


--
-- Name: alembic_version alembic_version_pkc; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.alembic_version
    ADD CONSTRAINT alembic_version_pkc PRIMARY KEY (version_num);


--
-- Name: document_versions pk_document_versions; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.document_versions
    ADD CONSTRAINT pk_document_versions PRIMARY KEY (id);


--
-- Name: documents pk_documents; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.documents
    ADD CONSTRAINT pk_documents PRIMARY KEY (id);


--
-- Name: ingestion_runs pk_ingestion_runs; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.ingestion_runs
    ADD CONSTRAINT pk_ingestion_runs PRIMARY KEY (id);


--
-- Name: source_endpoints pk_source_endpoints; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.source_endpoints
    ADD CONSTRAINT pk_source_endpoints PRIMARY KEY (id);


--
-- Name: sources pk_sources; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.sources
    ADD CONSTRAINT pk_sources PRIMARY KEY (id);


--
-- Name: document_versions uq_document_versions_document_hash; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.document_versions
    ADD CONSTRAINT uq_document_versions_document_hash UNIQUE (document_id, content_hash);


--
-- Name: document_versions uq_document_versions_document_version; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.document_versions
    ADD CONSTRAINT uq_document_versions_document_version UNIQUE (document_id, version_number);


--
-- Name: documents uq_documents_endpoint_external_id; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.documents
    ADD CONSTRAINT uq_documents_endpoint_external_id UNIQUE (source_endpoint_id, external_id);


--
-- Name: source_endpoints uq_source_endpoints_url; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.source_endpoints
    ADD CONSTRAINT uq_source_endpoints_url UNIQUE (url);


--
-- Name: sources uq_sources_website_url; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.sources
    ADD CONSTRAINT uq_sources_website_url UNIQUE (website_url);


--
-- Name: ix_document_versions_content_hash; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_document_versions_content_hash ON public.document_versions USING btree (content_hash);


--
-- Name: ix_document_versions_document_created_at; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_document_versions_document_created_at ON public.document_versions USING btree (document_id, created_at);


--
-- Name: ix_document_versions_document_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_document_versions_document_id ON public.document_versions USING btree (document_id);


--
-- Name: ix_documents_content_hash; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_documents_content_hash ON public.documents USING btree (content_hash);


--
-- Name: ix_documents_country; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_documents_country ON public.documents USING btree (country);


--
-- Name: ix_documents_endpoint_published_at; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_documents_endpoint_published_at ON public.documents USING btree (source_endpoint_id, published_at);


--
-- Name: ix_documents_language; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_documents_language ON public.documents USING btree (language);


--
-- Name: ix_documents_published_at; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_documents_published_at ON public.documents USING btree (published_at);


--
-- Name: ix_documents_retrieved_at; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_documents_retrieved_at ON public.documents USING btree (retrieved_at);


--
-- Name: ix_documents_source_endpoint_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_documents_source_endpoint_id ON public.documents USING btree (source_endpoint_id);


--
-- Name: ix_documents_source_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_documents_source_id ON public.documents USING btree (source_id);


--
-- Name: ix_documents_source_published_at; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_documents_source_published_at ON public.documents USING btree (source_id, published_at);


--
-- Name: ix_documents_source_type; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_documents_source_type ON public.documents USING btree (source_type);


--
-- Name: ix_documents_source_type_published_at; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_documents_source_type_published_at ON public.documents USING btree (source_type, published_at);


--
-- Name: ix_ingestion_runs_endpoint_started_at; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_ingestion_runs_endpoint_started_at ON public.ingestion_runs USING btree (source_endpoint_id, started_at);


--
-- Name: ix_ingestion_runs_source_started_at; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_ingestion_runs_source_started_at ON public.ingestion_runs USING btree (source_id, started_at);


--
-- Name: ix_ingestion_runs_status_started_at; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_ingestion_runs_status_started_at ON public.ingestion_runs USING btree (status, started_at);


--
-- Name: ix_source_endpoints_due_poll; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_source_endpoints_due_poll ON public.source_endpoints USING btree (status, next_poll_at);


--
-- Name: ix_source_endpoints_endpoint_type; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_source_endpoints_endpoint_type ON public.source_endpoints USING btree (endpoint_type);


--
-- Name: ix_source_endpoints_source_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_source_endpoints_source_id ON public.source_endpoints USING btree (source_id);


--
-- Name: ix_source_endpoints_source_status; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_source_endpoints_source_status ON public.source_endpoints USING btree (source_id, status);


--
-- Name: ix_source_endpoints_status; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_source_endpoints_status ON public.source_endpoints USING btree (status);


--
-- Name: ix_sources_country; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_sources_country ON public.sources USING btree (country);


--
-- Name: ix_sources_country_status; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_sources_country_status ON public.sources USING btree (country, status);


--
-- Name: ix_sources_priority; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_sources_priority ON public.sources USING btree (priority);


--
-- Name: ix_sources_source_type; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_sources_source_type ON public.sources USING btree (source_type);


--
-- Name: ix_sources_status; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_sources_status ON public.sources USING btree (status);


--
-- Name: ix_sources_type_status; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_sources_type_status ON public.sources USING btree (source_type, status);


--
-- Name: document_versions fk_document_versions_document_id_documents; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.document_versions
    ADD CONSTRAINT fk_document_versions_document_id_documents FOREIGN KEY (document_id) REFERENCES public.documents(id) ON DELETE CASCADE;


--
-- Name: documents fk_documents_source_endpoint_id_source_endpoints; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.documents
    ADD CONSTRAINT fk_documents_source_endpoint_id_source_endpoints FOREIGN KEY (source_endpoint_id) REFERENCES public.source_endpoints(id) ON DELETE SET NULL;


--
-- Name: documents fk_documents_source_id_sources; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.documents
    ADD CONSTRAINT fk_documents_source_id_sources FOREIGN KEY (source_id) REFERENCES public.sources(id) ON DELETE RESTRICT;


--
-- Name: ingestion_runs fk_ingestion_runs_source_endpoint_id_source_endpoints; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.ingestion_runs
    ADD CONSTRAINT fk_ingestion_runs_source_endpoint_id_source_endpoints FOREIGN KEY (source_endpoint_id) REFERENCES public.source_endpoints(id) ON DELETE SET NULL;


--
-- Name: ingestion_runs fk_ingestion_runs_source_id_sources; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.ingestion_runs
    ADD CONSTRAINT fk_ingestion_runs_source_id_sources FOREIGN KEY (source_id) REFERENCES public.sources(id) ON DELETE RESTRICT;


--
-- Name: source_endpoints fk_source_endpoints_source_id_sources; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.source_endpoints
    ADD CONSTRAINT fk_source_endpoints_source_id_sources FOREIGN KEY (source_id) REFERENCES public.sources(id) ON DELETE CASCADE;


--
-- PostgreSQL database dump complete
--

\unrestrict 7ZdDcXgV2H6rC33DbWHn88yJuZFlAStaZPcaXsyBbjImSVKZcwMz0upyrFfwbPZ

