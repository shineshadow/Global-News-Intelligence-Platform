--
-- PostgreSQL database dump
--

\restrict CrmfOXF6l65Jgm3ilY5Mr100DMYapjJPSKgBJTKmlaq8hj4yvx0LAmc963Gp8Fc

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

--
-- Name: calendar_reject_mutation(); Type: FUNCTION; Schema: public; Owner: -
--

CREATE FUNCTION public.calendar_reject_mutation() RETURNS trigger
    LANGUAGE plpgsql
    AS $$
        BEGIN
            RAISE EXCEPTION '% is append-only', TG_TABLE_NAME;
        END
        $$;


--
-- Name: calendar_restrict_assertion_mutation(); Type: FUNCTION; Schema: public; Owner: -
--

CREATE FUNCTION public.calendar_restrict_assertion_mutation() RETURNS trigger
    LANGUAGE plpgsql
    AS $$
        BEGIN
            IF TG_OP = 'UPDATE'
               AND OLD.retracted_at IS NULL
               AND NEW.retracted_at IS NOT NULL
               AND (to_jsonb(NEW) - 'retracted_at')
                   = (to_jsonb(OLD) - 'retracted_at')
            THEN
                RETURN NEW;
            END IF;
            RAISE EXCEPTION
                'Calendar assertions may only be retracted, never rewritten or deleted';
        END
        $$;


--
-- Name: calendar_restrict_recurrence_rule_mutation(); Type: FUNCTION; Schema: public; Owner: -
--

CREATE FUNCTION public.calendar_restrict_recurrence_rule_mutation() RETURNS trigger
    LANGUAGE plpgsql
    AS $$
        BEGIN
            IF OLD.status = 'active'
               AND NEW.status = 'superseded'
               AND (to_jsonb(NEW) - 'status') = (to_jsonb(OLD) - 'status')
            THEN
                RETURN NEW;
            END IF;
            RAISE EXCEPTION 'sealed recurrence rules are immutable';
        END
        $$;


--
-- Name: calendar_validate_event_shape(); Type: FUNCTION; Schema: public; Owner: -
--

CREATE FUNCTION public.calendar_validate_event_shape() RETURNS trigger
    LANGUAGE plpgsql
    AS $$
        DECLARE target_event_id bigint;
        DECLARE pattern text;
        DECLARE occurrence_count bigint;
        DECLARE active_rule_count bigint;
        DECLARE invalid_occurrence_count bigint;
        BEGIN
            IF TG_TABLE_NAME = 'intelligence_calendar_events' THEN
                target_event_id := COALESCE(NEW.id, OLD.id);
            ELSE
                target_event_id := COALESCE(NEW.event_id, OLD.event_id);
            END IF;
            SELECT schedule_pattern INTO pattern
            FROM intelligence_calendar_events WHERE id = target_event_id;
            IF pattern IS NULL THEN
                RETURN NULL;
            END IF;
            SELECT count(*) INTO occurrence_count
            FROM intelligence_calendar_event_occurrences
            WHERE event_id = target_event_id;
            SELECT count(*) INTO active_rule_count
            FROM intelligence_calendar_event_recurrence_rules
            WHERE event_id = target_event_id AND status = 'active';
            IF pattern = 'one_time' THEN
                IF occurrence_count <> 1 OR active_rule_count <> 0 OR EXISTS (
                    SELECT 1 FROM intelligence_calendar_event_occurrences
                    WHERE event_id = target_event_id
                      AND (
                          recurrence_rule_id IS NOT NULL
                          OR recurrence_key <> 'one_time'
                      )
                ) THEN
                    RAISE EXCEPTION
                        'one-time Event requires exactly one one-time Occurrence';
                END IF;
            ELSE
                SELECT count(*) INTO invalid_occurrence_count
                FROM intelligence_calendar_event_occurrences occurrence
                LEFT JOIN intelligence_calendar_event_recurrence_rules rule
                  ON rule.id = occurrence.recurrence_rule_id
                 AND rule.event_id = occurrence.event_id
                WHERE occurrence.event_id = target_event_id
                  AND rule.id IS NULL;
                IF active_rule_count <> 1 OR invalid_occurrence_count <> 0 THEN
                    RAISE EXCEPTION
                        'recurring Event requires one active rule and owned Occurrences';
                END IF;
            END IF;
            RETURN NULL;
        END
        $$;


--
-- Name: calendar_validate_evidence_source(); Type: FUNCTION; Schema: public; Owner: -
--

CREATE FUNCTION public.calendar_validate_evidence_source() RETURNS trigger
    LANGUAGE plpgsql
    AS $$
        DECLARE document_source_id bigint;
        BEGIN
            IF NEW.source_id IS NOT NULL AND NEW.document_id IS NOT NULL THEN
                SELECT source_id INTO document_source_id
                FROM documents WHERE id = NEW.document_id;
                IF document_source_id IS DISTINCT FROM NEW.source_id THEN
                    RAISE EXCEPTION
                        'evidence source does not own referenced document';
                END IF;
            END IF;
            RETURN NEW;
        END
        $$;


--
-- Name: calendar_validate_merge(); Type: FUNCTION; Schema: public; Owner: -
--

CREATE FUNCTION public.calendar_validate_merge() RETURNS trigger
    LANGUAGE plpgsql
    AS $$
        DECLARE current_target bigint;
        BEGIN
            current_target := NEW.winner_event_id;
            LOOP
                IF current_target = NEW.loser_event_id THEN
                    RAISE EXCEPTION 'Calendar Event merge cycle detected';
                END IF;
                SELECT merged_into_event_id INTO current_target
                FROM intelligence_calendar_events
                WHERE id = current_target;
                EXIT WHEN current_target IS NULL;
            END LOOP;
            IF NOT EXISTS (
                SELECT 1 FROM intelligence_calendar_events
                WHERE id = NEW.loser_event_id
                  AND identity_state = 'merged'
                  AND merged_into_event_id = NEW.winner_event_id
            ) THEN
                RAISE EXCEPTION
                    'loser must point to winner in merged identity state';
            END IF;
            RETURN NEW;
        END
        $$;


--
-- Name: calendar_validate_monitor_profile(); Type: FUNCTION; Schema: public; Owner: -
--

CREATE FUNCTION public.calendar_validate_monitor_profile() RETURNS trigger
    LANGUAGE plpgsql
    AS $$
        DECLARE policy_profile_id bigint;
        DECLARE monitor_profile_id bigint;
        BEGIN
            SELECT profile_id INTO policy_profile_id
            FROM intelligence_calendar_event_coverage_policies
            WHERE id = NEW.policy_id;
            SELECT coverage_profile_id INTO monitor_profile_id
            FROM monitors WHERE id = NEW.monitor_id;
            IF policy_profile_id IS DISTINCT FROM monitor_profile_id THEN
                RAISE EXCEPTION
                    'Calendar policy and Monitor Coverage Profiles differ';
            END IF;
            RETURN NEW;
        END
        $$;


--
-- Name: calendar_validate_policy_override(); Type: FUNCTION; Schema: public; Owner: -
--

CREATE FUNCTION public.calendar_validate_policy_override() RETURNS trigger
    LANGUAGE plpgsql
    AS $$
        DECLARE policy_event_id bigint;
        DECLARE occurrence_event_id bigint;
        BEGIN
            SELECT event_id INTO policy_event_id
            FROM intelligence_calendar_event_coverage_policies
            WHERE id = NEW.policy_id;
            SELECT event_id INTO occurrence_event_id
            FROM intelligence_calendar_event_occurrences
            WHERE id = NEW.occurrence_id;
            IF policy_event_id IS DISTINCT FROM occurrence_event_id THEN
                RAISE EXCEPTION
                    'occurrence override policy and occurrence events differ';
            END IF;
            RETURN NEW;
        END
        $$;


--
-- Name: calendar_validate_timezone(); Type: FUNCTION; Schema: public; Owner: -
--

CREATE FUNCTION public.calendar_validate_timezone() RETURNS trigger
    LANGUAGE plpgsql
    AS $$
        BEGIN
            IF NEW.timezone_name IS NOT NULL
               AND NOT EXISTS (
                   SELECT 1 FROM pg_timezone_names
                   WHERE name = NEW.timezone_name
               )
            THEN
                RAISE EXCEPTION 'invalid IANA timezone: %', NEW.timezone_name;
            END IF;
            RETURN NEW;
        END
        $$;


--
-- Name: calendar_validate_watch_endpoint(); Type: FUNCTION; Schema: public; Owner: -
--

CREATE FUNCTION public.calendar_validate_watch_endpoint() RETURNS trigger
    LANGUAGE plpgsql
    AS $$
        DECLARE endpoint_source_id bigint;
        BEGIN
            IF NEW.source_endpoint_id IS NOT NULL THEN
                SELECT source_id INTO endpoint_source_id
                FROM source_endpoints WHERE id = NEW.source_endpoint_id;
                IF endpoint_source_id IS DISTINCT FROM NEW.source_id THEN
                    RAISE EXCEPTION
                        'watch endpoint does not belong to watch source';
                END IF;
            END IF;
            RETURN NEW;
        END
        $$;


--
-- Name: preserve_alert_event(); Type: FUNCTION; Schema: public; Owner: -
--

CREATE FUNCTION public.preserve_alert_event() RETURNS trigger
    LANGUAGE plpgsql
    AS $$
        BEGIN
            RAISE EXCEPTION 'alert events are immutable';
        END;
        $$;


--
-- Name: preserve_completed_alert_attempt(); Type: FUNCTION; Schema: public; Owner: -
--

CREATE FUNCTION public.preserve_completed_alert_attempt() RETURNS trigger
    LANGUAGE plpgsql
    AS $$
        BEGIN
            IF TG_OP = 'DELETE' THEN
                RAISE EXCEPTION 'alert delivery attempts cannot be deleted';
            END IF;
            IF OLD.status <> 'running' THEN
                RAISE EXCEPTION
                    'completed alert delivery attempts are immutable';
            END IF;
            IF NEW.delivery_id IS DISTINCT FROM OLD.delivery_id
               OR NEW.attempt_number IS DISTINCT FROM OLD.attempt_number
               OR NEW.claim_token IS DISTINCT FROM OLD.claim_token
               OR NEW.request_url IS DISTINCT FROM OLD.request_url
               OR NEW.started_at IS DISTINCT FROM OLD.started_at
               OR NEW.metadata IS DISTINCT FROM OLD.metadata
               OR NEW.status = 'running' THEN
                RAISE EXCEPTION
                    'only completion fields may finalize an alert attempt';
            END IF;
            RETURN NEW;
        END;
        $$;


--
-- Name: preserve_monitor_revision_immutability(); Type: FUNCTION; Schema: public; Owner: -
--

CREATE FUNCTION public.preserve_monitor_revision_immutability() RETURNS trigger
    LANGUAGE plpgsql
    AS $$
        DECLARE
            inconsistent_hierarchy boolean;
        BEGIN
            IF TG_OP = 'DELETE' THEN
                IF OLD.sealed_at IS NOT NULL THEN
                    RAISE EXCEPTION
                        'sealed Monitor revisions cannot be deleted';
                END IF;
                RETURN OLD;
            END IF;

            IF OLD.sealed_at IS NOT NULL THEN
                RAISE EXCEPTION
                    'sealed Monitor revisions cannot be updated';
            END IF;
            IF NEW.sealed_at IS NULL THEN
                RAISE EXCEPTION
                    'the only permitted Monitor revision update is sealing';
            END IF;
            IF (
                NEW.id,
                NEW.monitor_id,
                NEW.revision_number,
                NEW.criteria_version,
                NEW.minimum_confidence,
                NEW.effective_from,
                NEW.text_query,
                NEW.match_all_in_profile,
                NEW.change_reason,
                NEW.created_at
            ) IS DISTINCT FROM (
                OLD.id,
                OLD.monitor_id,
                OLD.revision_number,
                OLD.criteria_version,
                OLD.minimum_confidence,
                OLD.effective_from,
                OLD.text_query,
                OLD.match_all_in_profile,
                OLD.change_reason,
                OLD.created_at
            ) THEN
                RAISE EXCEPTION
                    'Monitor revision criteria cannot change while sealing';
            END IF;

            SELECT EXISTS (
                SELECT 1
                FROM (
                    SELECT revision_id
                    FROM monitor_revision_geographies
                    WHERE revision_id = NEW.id
                    GROUP BY revision_id
                    HAVING count(DISTINCT include_descendants) > 1
                    UNION ALL
                    SELECT revision_id
                    FROM monitor_revision_topics
                    WHERE revision_id = NEW.id
                    GROUP BY revision_id
                    HAVING count(DISTINCT include_descendants) > 1
                    UNION ALL
                    SELECT revision_id
                    FROM monitor_revision_document_types
                    WHERE revision_id = NEW.id
                    GROUP BY revision_id
                    HAVING count(DISTINCT include_descendants) > 1
                    UNION ALL
                    SELECT revision_id
                    FROM monitor_revision_source_types
                    WHERE revision_id = NEW.id
                    GROUP BY revision_id
                    HAVING count(DISTINCT include_descendants) > 1
                ) AS mixed_policies
            ) INTO inconsistent_hierarchy;
            IF inconsistent_hierarchy THEN
                RAISE EXCEPTION
                    'one Monitor hierarchy dimension cannot mix descendant policies';
            END IF;

            RETURN NEW;
        END;
        $$;


--
-- Name: preserve_monitor_revision_selectors(); Type: FUNCTION; Schema: public; Owner: -
--

CREATE FUNCTION public.preserve_monitor_revision_selectors() RETURNS trigger
    LANGUAGE plpgsql
    AS $$
        DECLARE
            old_sealed timestamptz;
            new_sealed timestamptz;
        BEGIN
            IF TG_OP IN ('UPDATE', 'DELETE') THEN
                SELECT sealed_at INTO old_sealed
                FROM monitor_revisions
                WHERE id = OLD.revision_id;
                IF old_sealed IS NOT NULL THEN
                    RAISE EXCEPTION
                        'selectors of sealed Monitor revisions cannot change';
                END IF;
            END IF;
            IF TG_OP IN ('INSERT', 'UPDATE') THEN
                SELECT sealed_at INTO new_sealed
                FROM monitor_revisions
                WHERE id = NEW.revision_id;
                IF new_sealed IS NOT NULL THEN
                    RAISE EXCEPTION
                        'selectors cannot be added to a sealed Monitor revision';
                END IF;
            END IF;
            RETURN CASE WHEN TG_OP = 'DELETE' THEN OLD ELSE NEW END;
        END;
        $$;


--
-- Name: prevent_entity_type_hierarchy_cycle(); Type: FUNCTION; Schema: public; Owner: -
--

CREATE FUNCTION public.prevent_entity_type_hierarchy_cycle() RETURNS trigger
    LANGUAGE plpgsql
    AS $$
        BEGIN
            IF EXISTS (
                WITH RECURSIVE descendants(entity_type_id) AS (
                    SELECT child_entity_type_id
                    FROM entity_type_hierarchy_edges
                    WHERE parent_entity_type_id = NEW.child_entity_type_id

                    UNION

                    SELECT edge.child_entity_type_id
                    FROM entity_type_hierarchy_edges AS edge
                    JOIN descendants
                      ON edge.parent_entity_type_id =
                         descendants.entity_type_id
                )
                SELECT 1
                FROM descendants
                WHERE entity_type_id = NEW.parent_entity_type_id
            ) THEN
                RAISE EXCEPTION
                    'entity type hierarchy edge would create a cycle';
            END IF;

            RETURN NEW;
        END;
        $$;


--
-- Name: require_alert_match_provenance(); Type: FUNCTION; Schema: public; Owner: -
--

CREATE FUNCTION public.require_alert_match_provenance() RETURNS trigger
    LANGUAGE plpgsql
    AS $$
        BEGIN
            IF EXISTS (
                SELECT 1
                FROM alerts AS alert
                WHERE NOT EXISTS (
                    SELECT 1
                    FROM monitor_matches AS match
                    WHERE match.id = alert.monitor_match_id
                      AND match.monitor_id = alert.monitor_id
                      AND match.document_id = alert.document_id
                      AND match.first_monitor_revision_id =
                          alert.monitor_revision_id
                )
            ) THEN
                RAISE EXCEPTION
                    'alert provenance must match the originating Monitor match';
            END IF;
            RETURN NULL;
        END;
        $$;


--
-- Name: require_default_coverage_profile(); Type: FUNCTION; Schema: public; Owner: -
--

CREATE FUNCTION public.require_default_coverage_profile() RETURNS trigger
    LANGUAGE plpgsql
    AS $$
        BEGIN
            IF (
                SELECT count(*)
                FROM coverage_profiles
                WHERE is_default
                  AND is_active
            ) <> 1 THEN
                RAISE EXCEPTION
                    'exactly one active default coverage profile is required';
            END IF;
            RETURN NULL;
        END;
        $$;


--
-- Name: require_monitor_current_revision(); Type: FUNCTION; Schema: public; Owner: -
--

CREATE FUNCTION public.require_monitor_current_revision() RETURNS trigger
    LANGUAGE plpgsql
    AS $$
        BEGIN
            IF EXISTS (
                SELECT 1
                FROM monitors AS monitor
                WHERE NOT EXISTS (
                    SELECT 1
                    FROM monitor_revisions AS revision
                    WHERE revision.monitor_id = monitor.id
                      AND revision.revision_number =
                          monitor.current_revision_number
                      AND revision.sealed_at IS NOT NULL
                )
            ) THEN
                RAISE EXCEPTION
                    'every monitor must reference an existing sealed current revision';
            END IF;
            RETURN NULL;
        END;
        $$;


--
-- Name: require_monitor_revisions_sealed(); Type: FUNCTION; Schema: public; Owner: -
--

CREATE FUNCTION public.require_monitor_revisions_sealed() RETURNS trigger
    LANGUAGE plpgsql
    AS $$
        BEGIN
            IF EXISTS (
                SELECT 1
                FROM monitor_revisions
                WHERE sealed_at IS NULL
            ) THEN
                RAISE EXCEPTION
                    'every Monitor revision must be sealed before commit';
            END IF;
            RETURN NULL;
        END;
        $$;


SET default_tablespace = '';

SET default_table_access_method = heap;

--
-- Name: acquisition_methods; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.acquisition_methods (
    id bigint NOT NULL,
    slug character varying(50) NOT NULL,
    name character varying(100) NOT NULL,
    description text,
    is_active boolean DEFAULT true NOT NULL,
    metadata jsonb DEFAULT '{}'::jsonb NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL
);


--
-- Name: acquisition_methods_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.acquisition_methods_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: acquisition_methods_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.acquisition_methods_id_seq OWNED BY public.acquisition_methods.id;


--
-- Name: alembic_version; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.alembic_version (
    version_num character varying(32) NOT NULL
);


--
-- Name: alert_deliveries; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.alert_deliveries (
    id bigint NOT NULL,
    alert_id bigint NOT NULL,
    destination_id bigint NOT NULL,
    priority character varying(20) NOT NULL,
    base_url text NOT NULL,
    topic character varying(255) NOT NULL,
    auth_token_env_var character varying(255),
    request_timeout_seconds integer NOT NULL,
    max_attempts integer NOT NULL,
    retry_base_seconds integer NOT NULL,
    retry_max_seconds integer NOT NULL,
    status character varying(30) DEFAULT 'pending'::character varying NOT NULL,
    attempt_count integer DEFAULT 0 NOT NULL,
    cycle_attempt_count integer DEFAULT 0 NOT NULL,
    next_attempt_at timestamp with time zone DEFAULT now(),
    claimed_at timestamp with time zone,
    claim_expires_at timestamp with time zone,
    claim_token uuid,
    last_attempt_at timestamp with time zone,
    delivered_at timestamp with time zone,
    last_http_status integer,
    last_error text,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL,
    CONSTRAINT ck_alert_deliveries_attempt_count CHECK ((attempt_count >= 0)),
    CONSTRAINT ck_alert_deliveries_auth_env CHECK (((auth_token_env_var IS NULL) OR ((auth_token_env_var)::text ~ '^[A-Za-z_][A-Za-z0-9_]*$'::text))),
    CONSTRAINT ck_alert_deliveries_base_url CHECK ((base_url ~ '^https?://'::text)),
    CONSTRAINT ck_alert_deliveries_claim_state CHECK (((((status)::text = 'processing'::text) AND (claim_token IS NOT NULL) AND (claimed_at IS NOT NULL) AND (claim_expires_at IS NOT NULL)) OR (((status)::text <> 'processing'::text) AND (claim_token IS NULL) AND (claimed_at IS NULL) AND (claim_expires_at IS NULL)))),
    CONSTRAINT ck_alert_deliveries_cycle_attempt_count CHECK (((cycle_attempt_count >= 0) AND (cycle_attempt_count <= attempt_count))),
    CONSTRAINT ck_alert_deliveries_delivered_state CHECK ((((status)::text <> 'delivered'::text) OR (delivered_at IS NOT NULL))),
    CONSTRAINT ck_alert_deliveries_http_status CHECK (((last_http_status IS NULL) OR ((last_http_status >= 100) AND (last_http_status <= 599)))),
    CONSTRAINT ck_alert_deliveries_max_attempts CHECK (((max_attempts >= 1) AND (max_attempts <= 20))),
    CONSTRAINT ck_alert_deliveries_priority CHECK (((priority)::text = ANY ((ARRAY['low'::character varying, 'normal'::character varying, 'high'::character varying, 'critical'::character varying])::text[]))),
    CONSTRAINT ck_alert_deliveries_retry_base CHECK (((retry_base_seconds >= 1) AND (retry_base_seconds <= 86400))),
    CONSTRAINT ck_alert_deliveries_retry_max CHECK (((retry_max_seconds >= retry_base_seconds) AND (retry_max_seconds <= 604800))),
    CONSTRAINT ck_alert_deliveries_schedule_state CHECK (((((status)::text = ANY ((ARRAY['pending'::character varying, 'retry_scheduled'::character varying])::text[])) AND (next_attempt_at IS NOT NULL)) OR (((status)::text <> ALL ((ARRAY['pending'::character varying, 'retry_scheduled'::character varying])::text[])) AND (next_attempt_at IS NULL)))),
    CONSTRAINT ck_alert_deliveries_status CHECK (((status)::text = ANY ((ARRAY['pending'::character varying, 'processing'::character varying, 'retry_scheduled'::character varying, 'delivered'::character varying, 'permanent_failure'::character varying, 'cancelled'::character varying])::text[]))),
    CONSTRAINT ck_alert_deliveries_timeout CHECK (((request_timeout_seconds >= 1) AND (request_timeout_seconds <= 60))),
    CONSTRAINT ck_alert_deliveries_topic CHECK (((topic)::text ~ '^[A-Za-z0-9_-]+$'::text))
);


--
-- Name: alert_deliveries_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.alert_deliveries_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: alert_deliveries_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.alert_deliveries_id_seq OWNED BY public.alert_deliveries.id;


--
-- Name: alert_delivery_attempts; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.alert_delivery_attempts (
    id bigint NOT NULL,
    delivery_id bigint NOT NULL,
    attempt_number integer NOT NULL,
    claim_token uuid NOT NULL,
    status character varying(30) DEFAULT 'running'::character varying NOT NULL,
    request_url text NOT NULL,
    started_at timestamp with time zone DEFAULT now() NOT NULL,
    completed_at timestamp with time zone,
    http_status integer,
    error text,
    response_excerpt text,
    metadata jsonb DEFAULT '{}'::jsonb NOT NULL,
    CONSTRAINT ck_alert_delivery_attempts_completed_after_started CHECK (((completed_at IS NULL) OR (completed_at >= started_at))),
    CONSTRAINT ck_alert_delivery_attempts_completion CHECK (((((status)::text = 'running'::text) AND (completed_at IS NULL)) OR (((status)::text <> 'running'::text) AND (completed_at IS NOT NULL)))),
    CONSTRAINT ck_alert_delivery_attempts_http_status CHECK (((http_status IS NULL) OR ((http_status >= 100) AND (http_status <= 599)))),
    CONSTRAINT ck_alert_delivery_attempts_number CHECK ((attempt_number > 0)),
    CONSTRAINT ck_alert_delivery_attempts_status CHECK (((status)::text = ANY ((ARRAY['running'::character varying, 'succeeded'::character varying, 'retryable_failure'::character varying, 'permanent_failure'::character varying])::text[])))
);


--
-- Name: alert_delivery_attempts_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.alert_delivery_attempts_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: alert_delivery_attempts_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.alert_delivery_attempts_id_seq OWNED BY public.alert_delivery_attempts.id;


--
-- Name: alert_destinations; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.alert_destinations (
    id bigint NOT NULL,
    slug character varying(255) NOT NULL,
    name character varying(255) NOT NULL,
    channel character varying(20) DEFAULT 'ntfy'::character varying NOT NULL,
    base_url text NOT NULL,
    topic character varying(255) NOT NULL,
    auth_token_env_var character varying(255),
    is_active boolean DEFAULT true NOT NULL,
    request_timeout_seconds integer DEFAULT 10 NOT NULL,
    max_attempts integer DEFAULT 5 NOT NULL,
    retry_base_seconds integer DEFAULT 30 NOT NULL,
    retry_max_seconds integer DEFAULT 3600 NOT NULL,
    metadata jsonb DEFAULT '{}'::jsonb NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL,
    CONSTRAINT ck_alert_destinations_auth_env CHECK (((auth_token_env_var IS NULL) OR ((auth_token_env_var)::text ~ '^[A-Za-z_][A-Za-z0-9_]*$'::text))),
    CONSTRAINT ck_alert_destinations_base_url CHECK ((base_url ~ '^https?://'::text)),
    CONSTRAINT ck_alert_destinations_channel CHECK (((channel)::text = 'ntfy'::text)),
    CONSTRAINT ck_alert_destinations_max_attempts CHECK (((max_attempts >= 1) AND (max_attempts <= 20))),
    CONSTRAINT ck_alert_destinations_name_nonempty CHECK ((btrim((name)::text) <> ''::text)),
    CONSTRAINT ck_alert_destinations_retry_base CHECK (((retry_base_seconds >= 1) AND (retry_base_seconds <= 86400))),
    CONSTRAINT ck_alert_destinations_retry_max CHECK (((retry_max_seconds >= retry_base_seconds) AND (retry_max_seconds <= 604800))),
    CONSTRAINT ck_alert_destinations_slug_format CHECK (((slug)::text ~ '^[a-z0-9]+(_[a-z0-9]+)*$'::text)),
    CONSTRAINT ck_alert_destinations_timeout CHECK (((request_timeout_seconds >= 1) AND (request_timeout_seconds <= 60))),
    CONSTRAINT ck_alert_destinations_topic CHECK (((topic)::text ~ '^[A-Za-z0-9_-]+$'::text))
);


--
-- Name: alert_destinations_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.alert_destinations_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: alert_destinations_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.alert_destinations_id_seq OWNED BY public.alert_destinations.id;


--
-- Name: alerts; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.alerts (
    id bigint NOT NULL,
    alert_class character varying(50) DEFAULT 'content_monitor_match'::character varying NOT NULL,
    monitor_id bigint NOT NULL,
    monitor_match_id bigint NOT NULL,
    monitor_revision_id bigint NOT NULL,
    document_id bigint NOT NULL,
    priority character varying(20) DEFAULT 'normal'::character varying NOT NULL,
    title character varying(512) NOT NULL,
    message text NOT NULL,
    metadata jsonb DEFAULT '{}'::jsonb NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    CONSTRAINT ck_alerts_alert_class CHECK (((alert_class)::text = 'content_monitor_match'::text)),
    CONSTRAINT ck_alerts_message_nonempty CHECK ((btrim(message) <> ''::text)),
    CONSTRAINT ck_alerts_priority CHECK (((priority)::text = ANY ((ARRAY['low'::character varying, 'normal'::character varying, 'high'::character varying, 'critical'::character varying])::text[]))),
    CONSTRAINT ck_alerts_title_nonempty CHECK ((btrim((title)::text) <> ''::text))
);


--
-- Name: alerts_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.alerts_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: alerts_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.alerts_id_seq OWNED BY public.alerts.id;


--
-- Name: classification_runs; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.classification_runs (
    id bigint NOT NULL,
    document_id bigint NOT NULL,
    pipeline_version character varying(100) NOT NULL,
    taxonomy_version character varying(50) NOT NULL,
    started_at timestamp with time zone DEFAULT now() NOT NULL,
    completed_at timestamp with time zone,
    status character varying(30) DEFAULT 'running'::character varying NOT NULL,
    language character varying(255),
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


--
-- Name: classification_runs_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.classification_runs_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: classification_runs_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.classification_runs_id_seq OWNED BY public.classification_runs.id;


--
-- Name: content_formats; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.content_formats (
    id bigint NOT NULL,
    slug character varying(50) NOT NULL,
    name character varying(100) NOT NULL,
    description text,
    is_active boolean DEFAULT true NOT NULL,
    metadata jsonb DEFAULT '{}'::jsonb NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL
);


--
-- Name: content_formats_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.content_formats_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: content_formats_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.content_formats_id_seq OWNED BY public.content_formats.id;


--
-- Name: coverage_profile_content_formats; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.coverage_profile_content_formats (
    profile_id bigint NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    content_format_slug character varying(50) NOT NULL
);


--
-- Name: coverage_profile_document_types; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.coverage_profile_document_types (
    profile_id bigint NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    document_type_id bigint NOT NULL,
    include_descendants boolean DEFAULT false NOT NULL
);


--
-- Name: coverage_profile_geographies; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.coverage_profile_geographies (
    profile_id bigint NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    geography_id bigint NOT NULL,
    include_descendants boolean DEFAULT false NOT NULL
);


--
-- Name: coverage_profile_languages; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.coverage_profile_languages (
    profile_id bigint NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    language_tag character varying(255) NOT NULL
);


--
-- Name: coverage_profile_source_polling_overrides; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.coverage_profile_source_polling_overrides (
    profile_id bigint NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    source_id bigint NOT NULL,
    polling_priority character varying(20) NOT NULL,
    CONSTRAINT ck_coverage_profile_source_polling_overrides_polling_priority CHECK (((polling_priority)::text = ANY ((ARRAY['low'::character varying, 'normal'::character varying, 'high'::character varying, 'critical'::character varying])::text[])))
);


--
-- Name: coverage_profile_source_types; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.coverage_profile_source_types (
    profile_id bigint NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    source_type_slug character varying(50) NOT NULL,
    include_descendants boolean DEFAULT false NOT NULL
);


--
-- Name: coverage_profile_sources; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.coverage_profile_sources (
    profile_id bigint NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    source_id bigint NOT NULL
);


--
-- Name: coverage_profile_topics; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.coverage_profile_topics (
    profile_id bigint NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    topic_id bigint NOT NULL,
    include_descendants boolean DEFAULT false NOT NULL
);


--
-- Name: coverage_profile_translation_targets; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.coverage_profile_translation_targets (
    profile_id bigint NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    language_tag character varying(255) NOT NULL,
    preference_order integer NOT NULL,
    CONSTRAINT ck_coverage_profile_translation_targets_preference_orde_fda0 CHECK ((preference_order >= 0))
);


--
-- Name: coverage_profiles; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.coverage_profiles (
    id bigint NOT NULL,
    slug character varying(255) NOT NULL,
    name character varying(255) NOT NULL,
    description text,
    is_active boolean DEFAULT true NOT NULL,
    is_default boolean DEFAULT false NOT NULL,
    default_polling_priority character varying(20) DEFAULT 'normal'::character varying NOT NULL,
    metadata jsonb DEFAULT '{}'::jsonb NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL,
    CONSTRAINT ck_coverage_profiles_default_polling_priority CHECK (((default_polling_priority)::text = ANY ((ARRAY['low'::character varying, 'normal'::character varying, 'high'::character varying, 'critical'::character varying])::text[]))),
    CONSTRAINT ck_coverage_profiles_default_requires_active CHECK (((NOT is_default) OR is_active)),
    CONSTRAINT ck_coverage_profiles_name_nonempty CHECK ((btrim((name)::text) <> ''::text)),
    CONSTRAINT ck_coverage_profiles_slug_format CHECK (((slug)::text ~ '^[a-z0-9]+(_[a-z0-9]+)*$'::text))
);


--
-- Name: coverage_profiles_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.coverage_profiles_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: coverage_profiles_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.coverage_profiles_id_seq OWNED BY public.coverage_profiles.id;


--
-- Name: document_entities; Type: TABLE; Schema: public; Owner: -
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


--
-- Name: document_entities_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.document_entities_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: document_entities_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.document_entities_id_seq OWNED BY public.document_entities.id;


--
-- Name: document_geographies; Type: TABLE; Schema: public; Owner: -
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


--
-- Name: document_geographies_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.document_geographies_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: document_geographies_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.document_geographies_id_seq OWNED BY public.document_geographies.id;


--
-- Name: document_topics; Type: TABLE; Schema: public; Owner: -
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


--
-- Name: document_topics_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.document_topics_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: document_topics_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.document_topics_id_seq OWNED BY public.document_topics.id;


--
-- Name: document_type_assignments; Type: TABLE; Schema: public; Owner: -
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


--
-- Name: document_type_assignments_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.document_type_assignments_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: document_type_assignments_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.document_type_assignments_id_seq OWNED BY public.document_type_assignments.id;


--
-- Name: document_types; Type: TABLE; Schema: public; Owner: -
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


--
-- Name: document_types_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.document_types_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: document_types_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.document_types_id_seq OWNED BY public.document_types.id;


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
    language character varying(255),
    country character varying(100),
    author character varying(512),
    published_at timestamp with time zone,
    source_updated_at timestamp with time zone,
    retrieved_at timestamp with time zone NOT NULL,
    content_hash character varying(64) NOT NULL,
    changed_fields jsonb DEFAULT '[]'::jsonb NOT NULL,
    metadata jsonb DEFAULT '{}'::jsonb NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    content_format character varying(50) NOT NULL,
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
    external_id character varying(2048),
    canonical_url text,
    title_original text NOT NULL,
    summary_original text,
    content_original text,
    language character varying(255),
    country character varying(100),
    author character varying(512),
    published_at timestamp with time zone,
    source_updated_at timestamp with time zone,
    retrieved_at timestamp with time zone DEFAULT now() NOT NULL,
    content_hash character varying(64) NOT NULL,
    metadata jsonb DEFAULT '{}'::jsonb NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL,
    ingestion_format character varying(50) NOT NULL,
    content_format character varying(50) NOT NULL
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
-- Name: endpoint_formats; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.endpoint_formats (
    id bigint NOT NULL,
    slug character varying(50) NOT NULL,
    name character varying(100) NOT NULL,
    description text,
    is_active boolean DEFAULT true NOT NULL,
    metadata jsonb DEFAULT '{}'::jsonb NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL
);


--
-- Name: endpoint_formats_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.endpoint_formats_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: endpoint_formats_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.endpoint_formats_id_seq OWNED BY public.endpoint_formats.id;


--
-- Name: endpoint_types; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.endpoint_types (
    id bigint NOT NULL,
    slug character varying(50) NOT NULL,
    name character varying(100) NOT NULL,
    description text,
    is_active boolean DEFAULT true NOT NULL,
    metadata jsonb DEFAULT '{}'::jsonb NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL
);


--
-- Name: endpoint_types_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.endpoint_types_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: endpoint_types_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.endpoint_types_id_seq OWNED BY public.endpoint_types.id;


--
-- Name: entities; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.entities (
    id bigint NOT NULL,
    canonical_name character varying(512) NOT NULL,
    canonical_name_native character varying(512),
    is_active boolean DEFAULT true NOT NULL,
    metadata jsonb DEFAULT '{}'::jsonb NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL
);


--
-- Name: entities_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.entities_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: entities_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.entities_id_seq OWNED BY public.entities.id;


--
-- Name: entity_aliases; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.entity_aliases (
    id bigint NOT NULL,
    entity_id bigint NOT NULL,
    alias character varying(512) NOT NULL,
    language character varying(255) NOT NULL,
    script character varying(50),
    alias_type character varying(50),
    is_preferred boolean DEFAULT false NOT NULL,
    normalized_alias character varying(512) NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL
);


--
-- Name: entity_aliases_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.entity_aliases_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: entity_aliases_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.entity_aliases_id_seq OWNED BY public.entity_aliases.id;


--
-- Name: entity_geographies; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.entity_geographies (
    id bigint NOT NULL,
    confidence numeric(5,4),
    evidence jsonb DEFAULT '{}'::jsonb NOT NULL,
    provenance jsonb DEFAULT '{}'::jsonb NOT NULL,
    valid_from timestamp with time zone,
    valid_to timestamp with time zone,
    is_active boolean DEFAULT true NOT NULL,
    superseded_at timestamp with time zone,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL,
    entity_id bigint NOT NULL,
    geography_id bigint NOT NULL,
    relationship_type character varying(100) NOT NULL,
    assignment_method character varying(50) NOT NULL,
    CONSTRAINT ck_entity_geographies_confidence_range CHECK (((confidence IS NULL) OR ((confidence >= (0)::numeric) AND (confidence <= (1)::numeric)))),
    CONSTRAINT ck_entity_geographies_valid_interval CHECK (((valid_to IS NULL) OR (valid_from IS NULL) OR (valid_to >= valid_from)))
);


--
-- Name: entity_geographies_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.entity_geographies_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: entity_geographies_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.entity_geographies_id_seq OWNED BY public.entity_geographies.id;


--
-- Name: entity_geography_relationship_type_external_mappings; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.entity_geography_relationship_type_external_mappings (
    id bigint NOT NULL,
    confidence numeric(5,4),
    evidence jsonb DEFAULT '{}'::jsonb NOT NULL,
    provenance jsonb DEFAULT '{}'::jsonb NOT NULL,
    valid_from timestamp with time zone,
    valid_to timestamp with time zone,
    is_active boolean DEFAULT true NOT NULL,
    superseded_at timestamp with time zone,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL,
    relationship_type character varying(100) NOT NULL,
    external_resource_id bigint NOT NULL,
    mapping_relation character varying(50) NOT NULL,
    resource_kind character varying(50) DEFAULT 'property'::character varying NOT NULL,
    CONSTRAINT ck_entity_geography_relationship_type_external_mappings_1e59 CHECK (((resource_kind)::text = 'property'::text)),
    CONSTRAINT ck_entity_geography_relationship_type_external_mappings_4161 CHECK (((confidence IS NULL) OR ((confidence >= (0)::numeric) AND (confidence <= (1)::numeric)))),
    CONSTRAINT ck_entity_geography_relationship_type_external_mappings_d474 CHECK (((valid_to IS NULL) OR (valid_from IS NULL) OR (valid_to >= valid_from)))
);


--
-- Name: entity_geography_relationship_type_external_mappings_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.entity_geography_relationship_type_external_mappings_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: entity_geography_relationship_type_external_mappings_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.entity_geography_relationship_type_external_mappings_id_seq OWNED BY public.entity_geography_relationship_type_external_mappings.id;


--
-- Name: entity_geography_relationship_types; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.entity_geography_relationship_types (
    slug character varying(100) NOT NULL,
    name character varying(255) NOT NULL,
    description text,
    is_active boolean DEFAULT true NOT NULL,
    metadata jsonb DEFAULT '{}'::jsonb NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL
);


--
-- Name: entity_type_assignments; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.entity_type_assignments (
    id bigint NOT NULL,
    confidence numeric(5,4),
    evidence jsonb DEFAULT '{}'::jsonb NOT NULL,
    provenance jsonb DEFAULT '{}'::jsonb NOT NULL,
    valid_from timestamp with time zone,
    valid_to timestamp with time zone,
    is_active boolean DEFAULT true NOT NULL,
    superseded_at timestamp with time zone,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL,
    entity_id bigint NOT NULL,
    entity_type_id bigint NOT NULL,
    assignment_method character varying(50) NOT NULL,
    is_primary boolean DEFAULT false NOT NULL,
    CONSTRAINT ck_entity_type_assignments_confidence_range CHECK (((confidence IS NULL) OR ((confidence >= (0)::numeric) AND (confidence <= (1)::numeric)))),
    CONSTRAINT ck_entity_type_assignments_valid_interval CHECK (((valid_to IS NULL) OR (valid_from IS NULL) OR (valid_to >= valid_from)))
);


--
-- Name: entity_type_assignments_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.entity_type_assignments_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: entity_type_assignments_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.entity_type_assignments_id_seq OWNED BY public.entity_type_assignments.id;


--
-- Name: entity_type_external_mappings; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.entity_type_external_mappings (
    id bigint NOT NULL,
    confidence numeric(5,4),
    evidence jsonb DEFAULT '{}'::jsonb NOT NULL,
    provenance jsonb DEFAULT '{}'::jsonb NOT NULL,
    valid_from timestamp with time zone,
    valid_to timestamp with time zone,
    is_active boolean DEFAULT true NOT NULL,
    superseded_at timestamp with time zone,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL,
    entity_type_id bigint NOT NULL,
    external_resource_id bigint NOT NULL,
    mapping_relation character varying(50) NOT NULL,
    resource_kind character varying(50) NOT NULL,
    CONSTRAINT ck_entity_type_external_mappings_confidence_range CHECK (((confidence IS NULL) OR ((confidence >= (0)::numeric) AND (confidence <= (1)::numeric)))),
    CONSTRAINT ck_entity_type_external_mappings_resource_kind CHECK (((resource_kind)::text = ANY ((ARRAY['concept'::character varying, 'class'::character varying])::text[]))),
    CONSTRAINT ck_entity_type_external_mappings_valid_interval CHECK (((valid_to IS NULL) OR (valid_from IS NULL) OR (valid_to >= valid_from)))
);


--
-- Name: entity_type_external_mappings_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.entity_type_external_mappings_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: entity_type_external_mappings_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.entity_type_external_mappings_id_seq OWNED BY public.entity_type_external_mappings.id;


--
-- Name: entity_type_hierarchy_edges; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.entity_type_hierarchy_edges (
    id bigint NOT NULL,
    parent_entity_type_id bigint NOT NULL,
    child_entity_type_id bigint NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    CONSTRAINT ck_entity_type_hierarchy_edges_different_nodes CHECK ((parent_entity_type_id <> child_entity_type_id))
);


--
-- Name: entity_type_hierarchy_edges_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.entity_type_hierarchy_edges_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: entity_type_hierarchy_edges_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.entity_type_hierarchy_edges_id_seq OWNED BY public.entity_type_hierarchy_edges.id;


--
-- Name: entity_types; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.entity_types (
    id bigint NOT NULL,
    slug character varying(255) NOT NULL,
    name character varying(255) NOT NULL,
    description text,
    is_active boolean DEFAULT true NOT NULL,
    metadata jsonb DEFAULT '{}'::jsonb NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL
);


--
-- Name: entity_types_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.entity_types_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: entity_types_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.entity_types_id_seq OWNED BY public.entity_types.id;


--
-- Name: external_semantic_authorities; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.external_semantic_authorities (
    slug character varying(100) NOT NULL,
    name character varying(255) NOT NULL,
    description text,
    is_active boolean DEFAULT true NOT NULL,
    metadata jsonb DEFAULT '{}'::jsonb NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL,
    authority_uri text
);


--
-- Name: external_semantic_resource_kinds; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.external_semantic_resource_kinds (
    slug character varying(50) NOT NULL,
    name character varying(255) NOT NULL,
    description text,
    is_active boolean DEFAULT true NOT NULL,
    metadata jsonb DEFAULT '{}'::jsonb NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL
);


--
-- Name: external_semantic_resources; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.external_semantic_resources (
    id bigint NOT NULL,
    scheme_id bigint NOT NULL,
    resource_kind character varying(50) NOT NULL,
    external_identifier character varying(512) NOT NULL,
    external_uri text,
    name character varying(512),
    description text,
    source_created_at timestamp with time zone,
    source_modified_at timestamp with time zone,
    source_retired_at timestamp with time zone,
    is_active boolean DEFAULT true NOT NULL,
    metadata jsonb DEFAULT '{}'::jsonb NOT NULL,
    first_retrieved_at timestamp with time zone,
    last_retrieved_at timestamp with time zone,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL
);


--
-- Name: external_semantic_resources_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.external_semantic_resources_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: external_semantic_resources_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.external_semantic_resources_id_seq OWNED BY public.external_semantic_resources.id;


--
-- Name: external_semantic_schemes; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.external_semantic_schemes (
    id bigint NOT NULL,
    authority_slug character varying(100) NOT NULL,
    slug character varying(100) NOT NULL,
    name character varying(255) NOT NULL,
    scheme_uri text,
    preferred_prefix character varying(50),
    version_label character varying(100),
    version_date date,
    last_retrieved_at timestamp with time zone,
    is_active boolean DEFAULT true NOT NULL,
    metadata jsonb DEFAULT '{}'::jsonb NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL
);


--
-- Name: external_semantic_schemes_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.external_semantic_schemes_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: external_semantic_schemes_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.external_semantic_schemes_id_seq OWNED BY public.external_semantic_schemes.id;


--
-- Name: geographies; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.geographies (
    id bigint NOT NULL,
    parent_id bigint,
    slug character varying(255) NOT NULL,
    name character varying(255) NOT NULL,
    native_name character varying(255),
    geography_type character varying(50) NOT NULL,
    is_active boolean DEFAULT true NOT NULL,
    metadata jsonb DEFAULT '{}'::jsonb NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL,
    iso_alpha2 character varying(2),
    iso_alpha3 character varying(3),
    CONSTRAINT ck_geographies_ck_geographies_geography_type CHECK (((geography_type)::text = ANY ((ARRAY['world'::character varying, 'region'::character varying, 'subregion'::character varying, 'intermediate_region'::character varying, 'country_or_area'::character varying, 'country'::character varying, 'territory'::character varying, 'nation_or_homeland'::character varying, 'de_facto_state'::character varying, 'state_province'::character varying, 'city'::character varying, 'maritime_area'::character varying, 'custom_region'::character varying])::text[]))),
    CONSTRAINT ck_geographies_ck_geographies_iso_alpha2_format CHECK (((iso_alpha2 IS NULL) OR ((iso_alpha2)::text ~ '^[A-Z]{2}$'::text))),
    CONSTRAINT ck_geographies_ck_geographies_iso_alpha3_format CHECK (((iso_alpha3 IS NULL) OR ((iso_alpha3)::text ~ '^[A-Z]{3}$'::text)))
);


--
-- Name: geographies_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.geographies_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: geographies_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.geographies_id_seq OWNED BY public.geographies.id;


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
-- Name: intelligence_calendar_event_aliases; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.intelligence_calendar_event_aliases (
    id bigint NOT NULL,
    event_id bigint NOT NULL,
    alias character varying(500) NOT NULL,
    normalized_alias character varying(500) NOT NULL,
    language_tag character varying(255) NOT NULL,
    alias_type character varying(30) NOT NULL,
    valid_from timestamp with time zone DEFAULT now() NOT NULL,
    valid_to timestamp with time zone,
    provenance jsonb DEFAULT '{}'::jsonb NOT NULL,
    actor_kind character varying(20) DEFAULT 'operator'::character varying NOT NULL,
    actor_ref character varying(255),
    actor_label character varying(255),
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    CONSTRAINT ck_intelligence_calendar_event_aliases_actor_kind CHECK (((actor_kind)::text = ANY ((ARRAY['operator'::character varying, 'system'::character varying, 'import'::character varying, 'ai_job'::character varying])::text[]))),
    CONSTRAINT ck_intelligence_calendar_event_aliases_alias_nonempty CHECK ((btrim((alias)::text) <> ''::text)),
    CONSTRAINT ck_intelligence_calendar_event_aliases_alias_type CHECK (((alias_type)::text = ANY ((ARRAY['title'::character varying, 'short_name'::character varying, 'native_name'::character varying, 'former_name'::character varying])::text[]))),
    CONSTRAINT ck_intelligence_calendar_event_aliases_normalized_nonempty CHECK ((btrim((normalized_alias)::text) <> ''::text)),
    CONSTRAINT ck_intelligence_calendar_event_aliases_valid_interval CHECK (((valid_to IS NULL) OR (valid_to > valid_from)))
);


--
-- Name: intelligence_calendar_event_aliases_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.intelligence_calendar_event_aliases_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: intelligence_calendar_event_aliases_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.intelligence_calendar_event_aliases_id_seq OWNED BY public.intelligence_calendar_event_aliases.id;


--
-- Name: intelligence_calendar_event_coverage_policies; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.intelligence_calendar_event_coverage_policies (
    id bigint NOT NULL,
    event_id bigint NOT NULL,
    profile_id bigint NOT NULL,
    watch_state character varying(20) DEFAULT 'watch'::character varying NOT NULL,
    monitoring_priority character varying(20) DEFAULT 'normal'::character varying NOT NULL,
    expected_news_importance character varying(20) DEFAULT 'normal'::character varying NOT NULL,
    pre_event_window_seconds integer DEFAULT 86400 NOT NULL,
    post_event_window_seconds integer DEFAULT 86400 NOT NULL,
    reminder_alerts_enabled boolean DEFAULT false NOT NULL,
    change_alerts_enabled boolean DEFAULT false NOT NULL,
    polling_escalation_allowed boolean DEFAULT false NOT NULL,
    youtube_escalation_allowed boolean DEFAULT false NOT NULL,
    metadata jsonb DEFAULT '{}'::jsonb NOT NULL,
    actor_kind character varying(20) DEFAULT 'operator'::character varying NOT NULL,
    actor_ref character varying(255),
    actor_label character varying(255),
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL,
    CONSTRAINT ck_intelligence_calendar_event_coverage_policies_actor_kind CHECK (((actor_kind)::text = ANY ((ARRAY['operator'::character varying, 'system'::character varying, 'import'::character varying, 'ai_job'::character varying])::text[]))),
    CONSTRAINT ck_intelligence_calendar_event_coverage_policies_expect_00a6 CHECK (((expected_news_importance)::text = ANY ((ARRAY['low'::character varying, 'normal'::character varying, 'high'::character varying, 'critical'::character varying])::text[]))),
    CONSTRAINT ck_intelligence_calendar_event_coverage_policies_monito_f866 CHECK (((monitoring_priority)::text = ANY ((ARRAY['low'::character varying, 'normal'::character varying, 'high'::character varying, 'critical'::character varying])::text[]))),
    CONSTRAINT ck_intelligence_calendar_event_coverage_policies_watch_state CHECK (((watch_state)::text = ANY ((ARRAY['watch'::character varying, 'ignore'::character varying])::text[]))),
    CONSTRAINT ck_intelligence_calendar_event_coverage_policies_window_8a76 CHECK (((pre_event_window_seconds >= 0) AND (post_event_window_seconds >= 0)))
);


--
-- Name: intelligence_calendar_event_coverage_policies_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.intelligence_calendar_event_coverage_policies_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: intelligence_calendar_event_coverage_policies_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.intelligence_calendar_event_coverage_policies_id_seq OWNED BY public.intelligence_calendar_event_coverage_policies.id;


--
-- Name: intelligence_calendar_event_documents; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.intelligence_calendar_event_documents (
    id bigint NOT NULL,
    event_id bigint NOT NULL,
    occurrence_id bigint,
    document_id bigint NOT NULL,
    relationship_type character varying(40) NOT NULL,
    confidence numeric(5,4) NOT NULL,
    method character varying(50) NOT NULL,
    evidence_id bigint,
    provenance jsonb DEFAULT '{}'::jsonb NOT NULL,
    actor_kind character varying(20) DEFAULT 'operator'::character varying NOT NULL,
    actor_ref character varying(255),
    actor_label character varying(255),
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    CONSTRAINT ck_intelligence_calendar_event_documents_actor_kind CHECK (((actor_kind)::text = ANY ((ARRAY['operator'::character varying, 'system'::character varying, 'import'::character varying, 'ai_job'::character varying])::text[]))),
    CONSTRAINT ck_intelligence_calendar_event_documents_confidence CHECK (((confidence >= (0)::numeric) AND (confidence <= (1)::numeric))),
    CONSTRAINT ck_intelligence_calendar_event_documents_relationship_type CHECK (((relationship_type)::text = ANY ((ARRAY['announcement'::character varying, 'confirmation'::character varying, 'preview'::character varying, 'pre_event_analysis'::character varying, 'live_update'::character varying, 'result'::character varying, 'post_event_analysis'::character varying, 'cancellation'::character varying, 'postponement'::character varying, 'correction'::character varying])::text[])))
);


--
-- Name: intelligence_calendar_event_documents_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.intelligence_calendar_event_documents_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: intelligence_calendar_event_documents_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.intelligence_calendar_event_documents_id_seq OWNED BY public.intelligence_calendar_event_documents.id;


--
-- Name: intelligence_calendar_event_entities; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.intelligence_calendar_event_entities (
    id bigint NOT NULL,
    event_id bigint NOT NULL,
    entity_id bigint NOT NULL,
    role character varying(50) NOT NULL,
    confidence numeric(5,4) NOT NULL,
    method character varying(50) NOT NULL,
    evidence_id bigint,
    valid_from timestamp with time zone DEFAULT now() NOT NULL,
    retracted_at timestamp with time zone,
    provenance jsonb DEFAULT '{}'::jsonb NOT NULL,
    actor_kind character varying(20) DEFAULT 'operator'::character varying NOT NULL,
    actor_ref character varying(255),
    actor_label character varying(255),
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    CONSTRAINT ck_intelligence_calendar_event_entities_actor_kind CHECK (((actor_kind)::text = ANY ((ARRAY['operator'::character varying, 'system'::character varying, 'import'::character varying, 'ai_job'::character varying])::text[]))),
    CONSTRAINT ck_intelligence_calendar_event_entities_confidence CHECK (((confidence >= (0)::numeric) AND (confidence <= (1)::numeric))),
    CONSTRAINT ck_intelligence_calendar_event_entities_role CHECK (((role)::text = ANY ((ARRAY['organizer'::character varying, 'participant'::character varying, 'subject'::character varying, 'speaker'::character varying, 'host'::character varying])::text[]))),
    CONSTRAINT ck_intelligence_calendar_event_entities_role_nonempty CHECK ((btrim((role)::text) <> ''::text)),
    CONSTRAINT ck_intelligence_calendar_event_entities_valid_interval CHECK (((retracted_at IS NULL) OR (retracted_at >= valid_from)))
);


--
-- Name: intelligence_calendar_event_entities_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.intelligence_calendar_event_entities_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: intelligence_calendar_event_entities_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.intelligence_calendar_event_entities_id_seq OWNED BY public.intelligence_calendar_event_entities.id;


--
-- Name: intelligence_calendar_event_evidence; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.intelligence_calendar_event_evidence (
    id bigint NOT NULL,
    event_id bigint NOT NULL,
    occurrence_id bigint,
    evidence_kind character varying(20) NOT NULL,
    source_id bigint,
    document_id bigint,
    external_url text,
    assertion_text text,
    excerpt text,
    language_tag character varying(255),
    authority_score numeric(5,4) DEFAULT 0 NOT NULL,
    confidence numeric(5,4) NOT NULL,
    method character varying(50) NOT NULL,
    published_at timestamp with time zone,
    observed_at timestamp with time zone DEFAULT now() NOT NULL,
    fingerprint character varying(64) NOT NULL,
    provenance jsonb DEFAULT '{}'::jsonb NOT NULL,
    actor_kind character varying(20) DEFAULT 'operator'::character varying NOT NULL,
    actor_ref character varying(255),
    actor_label character varying(255),
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    CONSTRAINT ck_intelligence_calendar_event_evidence_actor_kind CHECK (((actor_kind)::text = ANY ((ARRAY['operator'::character varying, 'system'::character varying, 'import'::character varying, 'ai_job'::character varying])::text[]))),
    CONSTRAINT ck_intelligence_calendar_event_evidence_authority_score CHECK (((authority_score >= (0)::numeric) AND (authority_score <= (1)::numeric))),
    CONSTRAINT ck_intelligence_calendar_event_evidence_confidence CHECK (((confidence >= (0)::numeric) AND (confidence <= (1)::numeric))),
    CONSTRAINT ck_intelligence_calendar_event_evidence_evidence_kind CHECK (((evidence_kind)::text = ANY ((ARRAY['supports'::character varying, 'contradicts'::character varying, 'corrects'::character varying])::text[]))),
    CONSTRAINT ck_intelligence_calendar_event_evidence_reference_present CHECK (((source_id IS NOT NULL) OR (document_id IS NOT NULL) OR (external_url IS NOT NULL) OR (assertion_text IS NOT NULL)))
);


--
-- Name: intelligence_calendar_event_evidence_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.intelligence_calendar_event_evidence_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: intelligence_calendar_event_evidence_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.intelligence_calendar_event_evidence_id_seq OWNED BY public.intelligence_calendar_event_evidence.id;


--
-- Name: intelligence_calendar_event_geographies; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.intelligence_calendar_event_geographies (
    id bigint NOT NULL,
    event_id bigint NOT NULL,
    geography_id bigint NOT NULL,
    role character varying(50) NOT NULL,
    confidence numeric(5,4) NOT NULL,
    method character varying(50) NOT NULL,
    evidence_id bigint,
    valid_from timestamp with time zone DEFAULT now() NOT NULL,
    retracted_at timestamp with time zone,
    provenance jsonb DEFAULT '{}'::jsonb NOT NULL,
    actor_kind character varying(20) DEFAULT 'operator'::character varying NOT NULL,
    actor_ref character varying(255),
    actor_label character varying(255),
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    CONSTRAINT ck_intelligence_calendar_event_geographies_actor_kind CHECK (((actor_kind)::text = ANY ((ARRAY['operator'::character varying, 'system'::character varying, 'import'::character varying, 'ai_job'::character varying])::text[]))),
    CONSTRAINT ck_intelligence_calendar_event_geographies_confidence CHECK (((confidence >= (0)::numeric) AND (confidence <= (1)::numeric))),
    CONSTRAINT ck_intelligence_calendar_event_geographies_role CHECK (((role)::text = ANY ((ARRAY['venue'::character varying, 'jurisdiction'::character varying, 'affected_area'::character varying, 'participant_location'::character varying])::text[]))),
    CONSTRAINT ck_intelligence_calendar_event_geographies_role_nonempty CHECK ((btrim((role)::text) <> ''::text)),
    CONSTRAINT ck_intelligence_calendar_event_geographies_valid_interval CHECK (((retracted_at IS NULL) OR (retracted_at >= valid_from)))
);


--
-- Name: intelligence_calendar_event_geographies_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.intelligence_calendar_event_geographies_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: intelligence_calendar_event_geographies_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.intelligence_calendar_event_geographies_id_seq OWNED BY public.intelligence_calendar_event_geographies.id;


--
-- Name: intelligence_calendar_event_merge_history; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.intelligence_calendar_event_merge_history (
    id bigint NOT NULL,
    winner_event_id bigint NOT NULL,
    loser_event_id bigint NOT NULL,
    reason text NOT NULL,
    evidence_id bigint,
    merged_at timestamp with time zone DEFAULT now() NOT NULL,
    actor_kind character varying(20) DEFAULT 'operator'::character varying NOT NULL,
    actor_ref character varying(255),
    actor_label character varying(255),
    CONSTRAINT ck_intelligence_calendar_event_merge_history_actor_kind CHECK (((actor_kind)::text = ANY ((ARRAY['operator'::character varying, 'system'::character varying, 'import'::character varying, 'ai_job'::character varying])::text[]))),
    CONSTRAINT ck_intelligence_calendar_event_merge_history_different_events CHECK ((winner_event_id <> loser_event_id)),
    CONSTRAINT ck_intelligence_calendar_event_merge_history_reason_nonempty CHECK ((btrim(reason) <> ''::text))
);


--
-- Name: intelligence_calendar_event_merge_history_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.intelligence_calendar_event_merge_history_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: intelligence_calendar_event_merge_history_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.intelligence_calendar_event_merge_history_id_seq OWNED BY public.intelligence_calendar_event_merge_history.id;


--
-- Name: intelligence_calendar_event_monitors; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.intelligence_calendar_event_monitors (
    id bigint NOT NULL,
    event_id bigint NOT NULL,
    occurrence_id bigint,
    policy_id bigint NOT NULL,
    monitor_id bigint NOT NULL,
    purpose character varying(30) NOT NULL,
    is_calendar_managed boolean DEFAULT false NOT NULL,
    activation_at timestamp with time zone,
    deactivation_at timestamp with time zone,
    link_status character varying(20) DEFAULT 'linked'::character varying NOT NULL,
    actor_kind character varying(20) DEFAULT 'operator'::character varying NOT NULL,
    actor_ref character varying(255),
    actor_label character varying(255),
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL,
    CONSTRAINT ck_intelligence_calendar_event_monitors_activation_interval CHECK (((deactivation_at IS NULL) OR (deactivation_at > activation_at))),
    CONSTRAINT ck_intelligence_calendar_event_monitors_actor_kind CHECK (((actor_kind)::text = ANY ((ARRAY['operator'::character varying, 'system'::character varying, 'import'::character varying, 'ai_job'::character varying])::text[]))),
    CONSTRAINT ck_intelligence_calendar_event_monitors_link_status CHECK (((link_status)::text = ANY ((ARRAY['linked'::character varying, 'active'::character varying, 'inactive'::character varying, 'retired'::character varying])::text[]))),
    CONSTRAINT ck_intelligence_calendar_event_monitors_purpose CHECK (((purpose)::text = ANY ((ARRAY['standing_series'::character varying, 'pre_event'::character varying, 'live'::character varying, 'post_event'::character varying])::text[])))
);


--
-- Name: intelligence_calendar_event_monitors_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.intelligence_calendar_event_monitors_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: intelligence_calendar_event_monitors_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.intelligence_calendar_event_monitors_id_seq OWNED BY public.intelligence_calendar_event_monitors.id;


--
-- Name: intelligence_calendar_event_occurrences; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.intelligence_calendar_event_occurrences (
    id bigint NOT NULL,
    public_id uuid DEFAULT gen_random_uuid() NOT NULL,
    event_id bigint NOT NULL,
    recurrence_rule_id bigint,
    recurrence_key character varying(255) NOT NULL,
    schedule_state character varying(20) DEFAULT 'scheduled'::character varying NOT NULL,
    validation_state character varying(20),
    current_schedule_revision_id bigint NOT NULL,
    metadata jsonb DEFAULT '{}'::jsonb NOT NULL,
    actor_kind character varying(20) DEFAULT 'operator'::character varying NOT NULL,
    actor_ref character varying(255),
    actor_label character varying(255),
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL,
    CONSTRAINT ck_intelligence_calendar_event_occurrences_actor_kind CHECK (((actor_kind)::text = ANY ((ARRAY['operator'::character varying, 'system'::character varying, 'import'::character varying, 'ai_job'::character varying])::text[]))),
    CONSTRAINT ck_intelligence_calendar_event_occurrences_key_nonempty CHECK ((btrim((recurrence_key)::text) <> ''::text)),
    CONSTRAINT ck_intelligence_calendar_event_occurrences_schedule_state CHECK (((schedule_state)::text = ANY ((ARRAY['tentative'::character varying, 'scheduled'::character varying, 'postponed'::character varying, 'cancelled'::character varying])::text[]))),
    CONSTRAINT ck_intelligence_calendar_event_occurrences_validation_state CHECK (((validation_state IS NULL) OR ((validation_state)::text = ANY ((ARRAY['candidate'::character varying, 'probable'::character varying, 'verified'::character varying, 'confirmed'::character varying, 'disputed'::character varying, 'rejected'::character varying])::text[]))))
);


--
-- Name: intelligence_calendar_event_occurrences_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.intelligence_calendar_event_occurrences_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: intelligence_calendar_event_occurrences_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.intelligence_calendar_event_occurrences_id_seq OWNED BY public.intelligence_calendar_event_occurrences.id;


--
-- Name: intelligence_calendar_event_recurrence_exceptions; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.intelligence_calendar_event_recurrence_exceptions (
    id bigint NOT NULL,
    recurrence_rule_id bigint NOT NULL,
    recurrence_key character varying(255) NOT NULL,
    exception_type character varying(20) NOT NULL,
    reason text,
    actor_kind character varying(20) DEFAULT 'operator'::character varying NOT NULL,
    actor_ref character varying(255),
    actor_label character varying(255),
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    CONSTRAINT ck_intelligence_calendar_event_recurrence_exceptions_actor_kind CHECK (((actor_kind)::text = ANY ((ARRAY['operator'::character varying, 'system'::character varying, 'import'::character varying, 'ai_job'::character varying])::text[]))),
    CONSTRAINT ck_intelligence_calendar_event_recurrence_exceptions_ex_7e5d CHECK (((exception_type)::text = ANY ((ARRAY['excluded'::character varying, 'added'::character varying])::text[]))),
    CONSTRAINT ck_intelligence_calendar_event_recurrence_exceptions_ke_3512 CHECK ((btrim((recurrence_key)::text) <> ''::text))
);


--
-- Name: intelligence_calendar_event_recurrence_exceptions_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.intelligence_calendar_event_recurrence_exceptions_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: intelligence_calendar_event_recurrence_exceptions_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.intelligence_calendar_event_recurrence_exceptions_id_seq OWNED BY public.intelligence_calendar_event_recurrence_exceptions.id;


--
-- Name: intelligence_calendar_event_recurrence_rules; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.intelligence_calendar_event_recurrence_rules (
    id bigint NOT NULL,
    event_id bigint NOT NULL,
    version_number integer NOT NULL,
    status character varying(20) DEFAULT 'active'::character varying NOT NULL,
    rrule text NOT NULL,
    dtstart_local timestamp without time zone,
    dtstart_date date,
    timezone_name character varying(255),
    all_day boolean NOT NULL,
    duration_seconds integer,
    materialization_horizon_days integer DEFAULT 730 NOT NULL,
    sealed_at timestamp with time zone DEFAULT now() NOT NULL,
    metadata jsonb DEFAULT '{}'::jsonb NOT NULL,
    actor_kind character varying(20) DEFAULT 'operator'::character varying NOT NULL,
    actor_ref character varying(255),
    actor_label character varying(255),
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    CONSTRAINT ck_intelligence_calendar_event_recurrence_rules_actor_kind CHECK (((actor_kind)::text = ANY ((ARRAY['operator'::character varying, 'system'::character varying, 'import'::character varying, 'ai_job'::character varying])::text[]))),
    CONSTRAINT ck_intelligence_calendar_event_recurrence_rules_duratio_6c64 CHECK (((duration_seconds IS NULL) OR (duration_seconds > 0))),
    CONSTRAINT ck_intelligence_calendar_event_recurrence_rules_horizon CHECK (((materialization_horizon_days >= 1) AND (materialization_horizon_days <= 3660))),
    CONSTRAINT ck_intelligence_calendar_event_recurrence_rules_start_mode CHECK (((all_day AND (dtstart_date IS NOT NULL) AND (dtstart_local IS NULL) AND (timezone_name IS NULL)) OR ((NOT all_day) AND (dtstart_local IS NOT NULL) AND (dtstart_date IS NULL) AND (timezone_name IS NOT NULL)))),
    CONSTRAINT ck_intelligence_calendar_event_recurrence_rules_status CHECK (((status)::text = ANY ((ARRAY['active'::character varying, 'superseded'::character varying])::text[]))),
    CONSTRAINT ck_intelligence_calendar_event_recurrence_rules_version_0e93 CHECK ((version_number > 0))
);


--
-- Name: intelligence_calendar_event_recurrence_rules_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.intelligence_calendar_event_recurrence_rules_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: intelligence_calendar_event_recurrence_rules_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.intelligence_calendar_event_recurrence_rules_id_seq OWNED BY public.intelligence_calendar_event_recurrence_rules.id;


--
-- Name: intelligence_calendar_event_revisions; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.intelligence_calendar_event_revisions (
    id bigint NOT NULL,
    event_id bigint NOT NULL,
    revision_number integer NOT NULL,
    title character varying(500) NOT NULL,
    description text,
    original_language_tag character varying(255),
    discovery_method character varying(40) DEFAULT 'manual'::character varying NOT NULL,
    change_reason text,
    sealed_at timestamp with time zone DEFAULT now() NOT NULL,
    metadata jsonb DEFAULT '{}'::jsonb NOT NULL,
    actor_kind character varying(20) DEFAULT 'operator'::character varying NOT NULL,
    actor_ref character varying(255),
    actor_label character varying(255),
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    CONSTRAINT ck_intelligence_calendar_event_revisions_actor_kind CHECK (((actor_kind)::text = ANY ((ARRAY['operator'::character varying, 'system'::character varying, 'import'::character varying, 'ai_job'::character varying])::text[]))),
    CONSTRAINT ck_intelligence_calendar_event_revisions_discovery_method CHECK (((discovery_method)::text = ANY ((ARRAY['manual'::character varying, 'recurring_event_research'::character varying, 'document_extraction'::character varying, 'official_calendar'::character varying, 'ai_discovered'::character varying])::text[]))),
    CONSTRAINT ck_intelligence_calendar_event_revisions_revision_positive CHECK ((revision_number > 0)),
    CONSTRAINT ck_intelligence_calendar_event_revisions_title_nonempty CHECK ((btrim((title)::text) <> ''::text))
);


--
-- Name: intelligence_calendar_event_revisions_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.intelligence_calendar_event_revisions_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: intelligence_calendar_event_revisions_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.intelligence_calendar_event_revisions_id_seq OWNED BY public.intelligence_calendar_event_revisions.id;


--
-- Name: intelligence_calendar_event_sources; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.intelligence_calendar_event_sources (
    id bigint NOT NULL,
    event_id bigint NOT NULL,
    source_id bigint NOT NULL,
    role character varying(50) NOT NULL,
    confidence numeric(5,4) NOT NULL,
    method character varying(50) NOT NULL,
    evidence_id bigint,
    valid_from timestamp with time zone DEFAULT now() NOT NULL,
    retracted_at timestamp with time zone,
    provenance jsonb DEFAULT '{}'::jsonb NOT NULL,
    actor_kind character varying(20) DEFAULT 'operator'::character varying NOT NULL,
    actor_ref character varying(255),
    actor_label character varying(255),
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    CONSTRAINT ck_intelligence_calendar_event_sources_actor_kind CHECK (((actor_kind)::text = ANY ((ARRAY['operator'::character varying, 'system'::character varying, 'import'::character varying, 'ai_job'::character varying])::text[]))),
    CONSTRAINT ck_intelligence_calendar_event_sources_confidence CHECK (((confidence >= (0)::numeric) AND (confidence <= (1)::numeric))),
    CONSTRAINT ck_intelligence_calendar_event_sources_role CHECK (((role)::text = ANY ((ARRAY['official'::character varying, 'expected'::character varying, 'reference'::character varying])::text[]))),
    CONSTRAINT ck_intelligence_calendar_event_sources_role_nonempty CHECK ((btrim((role)::text) <> ''::text)),
    CONSTRAINT ck_intelligence_calendar_event_sources_valid_interval CHECK (((retracted_at IS NULL) OR (retracted_at >= valid_from)))
);


--
-- Name: intelligence_calendar_event_sources_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.intelligence_calendar_event_sources_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: intelligence_calendar_event_sources_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.intelligence_calendar_event_sources_id_seq OWNED BY public.intelligence_calendar_event_sources.id;


--
-- Name: intelligence_calendar_event_state_transitions; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.intelligence_calendar_event_state_transitions (
    id bigint NOT NULL,
    event_id bigint NOT NULL,
    occurrence_id bigint,
    dimension character varying(20) NOT NULL,
    previous_state character varying(30) NOT NULL,
    next_state character varying(30) NOT NULL,
    reason text,
    evidence_id bigint,
    transitioned_at timestamp with time zone DEFAULT now() NOT NULL,
    actor_kind character varying(20) DEFAULT 'operator'::character varying NOT NULL,
    actor_ref character varying(255),
    actor_label character varying(255),
    CONSTRAINT ck_intelligence_calendar_event_state_transitions_actor_kind CHECK (((actor_kind)::text = ANY ((ARRAY['operator'::character varying, 'system'::character varying, 'import'::character varying, 'ai_job'::character varying])::text[]))),
    CONSTRAINT ck_intelligence_calendar_event_state_transitions_dimens_37c8 CHECK (((((dimension)::text = 'identity'::text) AND ((previous_state)::text = ANY ((ARRAY['active'::character varying, 'archived'::character varying, 'merged'::character varying])::text[])) AND ((next_state)::text = ANY ((ARRAY['active'::character varying, 'archived'::character varying, 'merged'::character varying])::text[]))) OR (((dimension)::text = 'validation'::text) AND ((previous_state)::text = ANY ((ARRAY['candidate'::character varying, 'probable'::character varying, 'verified'::character varying, 'confirmed'::character varying, 'disputed'::character varying, 'rejected'::character varying])::text[])) AND ((next_state)::text = ANY ((ARRAY['candidate'::character varying, 'probable'::character varying, 'verified'::character varying, 'confirmed'::character varying, 'disputed'::character varying, 'rejected'::character varying])::text[]))) OR (((dimension)::text = 'schedule'::text) AND ((previous_state)::text = ANY ((ARRAY['tentative'::character varying, 'scheduled'::character varying, 'postponed'::character varying, 'cancelled'::character varying])::text[])) AND ((next_state)::text = ANY ((ARRAY['tentative'::character varying, 'scheduled'::character varying, 'postponed'::character varying, 'cancelled'::character varying])::text[]))) OR (((dimension)::text = 'outcome'::text) AND ((previous_state)::text = ANY ((ARRAY['pending'::character varying, 'in_progress'::character varying, 'occurred'::character varying, 'partially_occurred'::character varying, 'did_not_occur'::character varying, 'unknown'::character varying])::text[])) AND ((next_state)::text = ANY ((ARRAY['pending'::character varying, 'in_progress'::character varying, 'occurred'::character varying, 'partially_occurred'::character varying, 'did_not_occur'::character varying, 'unknown'::character varying])::text[]))))),
    CONSTRAINT ck_intelligence_calendar_event_state_transitions_dimension CHECK (((dimension)::text = ANY ((ARRAY['identity'::character varying, 'validation'::character varying, 'schedule'::character varying, 'outcome'::character varying])::text[]))),
    CONSTRAINT ck_intelligence_calendar_event_state_transitions_schedu_9990 CHECK (((((dimension)::text = 'schedule'::text) AND (occurrence_id IS NOT NULL)) OR ((dimension)::text <> 'schedule'::text))),
    CONSTRAINT ck_intelligence_calendar_event_state_transitions_state_changes CHECK (((previous_state)::text <> (next_state)::text))
);


--
-- Name: intelligence_calendar_event_state_transitions_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.intelligence_calendar_event_state_transitions_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: intelligence_calendar_event_state_transitions_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.intelligence_calendar_event_state_transitions_id_seq OWNED BY public.intelligence_calendar_event_state_transitions.id;


--
-- Name: intelligence_calendar_event_topics; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.intelligence_calendar_event_topics (
    id bigint NOT NULL,
    event_id bigint NOT NULL,
    topic_id bigint NOT NULL,
    role character varying(50) NOT NULL,
    confidence numeric(5,4) NOT NULL,
    method character varying(50) NOT NULL,
    evidence_id bigint,
    valid_from timestamp with time zone DEFAULT now() NOT NULL,
    retracted_at timestamp with time zone,
    provenance jsonb DEFAULT '{}'::jsonb NOT NULL,
    actor_kind character varying(20) DEFAULT 'operator'::character varying NOT NULL,
    actor_ref character varying(255),
    actor_label character varying(255),
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    CONSTRAINT ck_intelligence_calendar_event_topics_actor_kind CHECK (((actor_kind)::text = ANY ((ARRAY['operator'::character varying, 'system'::character varying, 'import'::character varying, 'ai_job'::character varying])::text[]))),
    CONSTRAINT ck_intelligence_calendar_event_topics_confidence CHECK (((confidence >= (0)::numeric) AND (confidence <= (1)::numeric))),
    CONSTRAINT ck_intelligence_calendar_event_topics_role CHECK (((role)::text = ANY ((ARRAY['primary'::character varying, 'secondary'::character varying])::text[]))),
    CONSTRAINT ck_intelligence_calendar_event_topics_role_nonempty CHECK ((btrim((role)::text) <> ''::text)),
    CONSTRAINT ck_intelligence_calendar_event_topics_valid_interval CHECK (((retracted_at IS NULL) OR (retracted_at >= valid_from)))
);


--
-- Name: intelligence_calendar_event_topics_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.intelligence_calendar_event_topics_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: intelligence_calendar_event_topics_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.intelligence_calendar_event_topics_id_seq OWNED BY public.intelligence_calendar_event_topics.id;


--
-- Name: intelligence_calendar_events; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.intelligence_calendar_events (
    id bigint NOT NULL,
    public_id uuid DEFAULT gen_random_uuid() NOT NULL,
    schedule_pattern character varying(20) NOT NULL,
    identity_state character varying(20) DEFAULT 'active'::character varying NOT NULL,
    validation_state character varying(20) DEFAULT 'candidate'::character varying NOT NULL,
    current_revision_id bigint NOT NULL,
    merged_into_event_id bigint,
    metadata jsonb DEFAULT '{}'::jsonb NOT NULL,
    actor_kind character varying(20) DEFAULT 'operator'::character varying NOT NULL,
    actor_ref character varying(255),
    actor_label character varying(255),
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL,
    CONSTRAINT ck_intelligence_calendar_events_actor_kind CHECK (((actor_kind)::text = ANY ((ARRAY['operator'::character varying, 'system'::character varying, 'import'::character varying, 'ai_job'::character varying])::text[]))),
    CONSTRAINT ck_intelligence_calendar_events_identity_state CHECK (((identity_state)::text = ANY ((ARRAY['active'::character varying, 'archived'::character varying, 'merged'::character varying])::text[]))),
    CONSTRAINT ck_intelligence_calendar_events_merge_state CHECK (((((identity_state)::text = 'merged'::text) AND (merged_into_event_id IS NOT NULL)) OR (((identity_state)::text <> 'merged'::text) AND (merged_into_event_id IS NULL)))),
    CONSTRAINT ck_intelligence_calendar_events_not_self_merged CHECK (((merged_into_event_id IS NULL) OR (merged_into_event_id <> id))),
    CONSTRAINT ck_intelligence_calendar_events_schedule_pattern CHECK (((schedule_pattern)::text = ANY ((ARRAY['one_time'::character varying, 'recurring'::character varying])::text[]))),
    CONSTRAINT ck_intelligence_calendar_events_validation_state CHECK (((validation_state)::text = ANY ((ARRAY['candidate'::character varying, 'probable'::character varying, 'verified'::character varying, 'confirmed'::character varying, 'disputed'::character varying, 'rejected'::character varying])::text[])))
);


--
-- Name: intelligence_calendar_events_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.intelligence_calendar_events_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: intelligence_calendar_events_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.intelligence_calendar_events_id_seq OWNED BY public.intelligence_calendar_events.id;


--
-- Name: intelligence_calendar_occurrence_policy_overrides; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.intelligence_calendar_occurrence_policy_overrides (
    id bigint NOT NULL,
    policy_id bigint NOT NULL,
    occurrence_id bigint NOT NULL,
    monitoring_priority character varying(20),
    expected_news_importance character varying(20),
    is_watched boolean,
    metadata jsonb DEFAULT '{}'::jsonb NOT NULL,
    actor_kind character varying(20) DEFAULT 'operator'::character varying NOT NULL,
    actor_ref character varying(255),
    actor_label character varying(255),
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL,
    CONSTRAINT ck_intelligence_calendar_occurrence_policy_overrides_actor_kind CHECK (((actor_kind)::text = ANY ((ARRAY['operator'::character varying, 'system'::character varying, 'import'::character varying, 'ai_job'::character varying])::text[]))),
    CONSTRAINT ck_intelligence_calendar_occurrence_policy_overrides_ex_0077 CHECK (((expected_news_importance IS NULL) OR ((expected_news_importance)::text = ANY ((ARRAY['low'::character varying, 'normal'::character varying, 'high'::character varying, 'critical'::character varying])::text[])))),
    CONSTRAINT ck_intelligence_calendar_occurrence_policy_overrides_mo_88ee CHECK (((monitoring_priority IS NULL) OR ((monitoring_priority)::text = ANY ((ARRAY['low'::character varying, 'normal'::character varying, 'high'::character varying, 'critical'::character varying])::text[]))))
);


--
-- Name: intelligence_calendar_occurrence_policy_overrides_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.intelligence_calendar_occurrence_policy_overrides_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: intelligence_calendar_occurrence_policy_overrides_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.intelligence_calendar_occurrence_policy_overrides_id_seq OWNED BY public.intelligence_calendar_occurrence_policy_overrides.id;


--
-- Name: intelligence_calendar_occurrence_schedule_revisions; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.intelligence_calendar_occurrence_schedule_revisions (
    id bigint NOT NULL,
    occurrence_id bigint NOT NULL,
    revision_number integer NOT NULL,
    temporal_mode character varying(20) NOT NULL,
    scheduled_start_at timestamp with time zone,
    scheduled_end_at timestamp with time zone,
    start_date date,
    end_date_exclusive date,
    timezone_name character varying(255),
    utc_offset_original character varying(10),
    date_precision character varying(20) NOT NULL,
    time_precision character varying(20) NOT NULL,
    all_day boolean DEFAULT false NOT NULL,
    original_text text,
    original_language_tag character varying(255),
    normalization_method character varying(50) DEFAULT 'manual'::character varying NOT NULL,
    normalization_reference_at timestamp with time zone,
    change_reason text,
    sealed_at timestamp with time zone DEFAULT now() NOT NULL,
    metadata jsonb DEFAULT '{}'::jsonb NOT NULL,
    actor_kind character varying(20) DEFAULT 'operator'::character varying NOT NULL,
    actor_ref character varying(255),
    actor_label character varying(255),
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    CONSTRAINT ck_intelligence_calendar_occurrence_schedule_revisions__0a53 CHECK (((actor_kind)::text = ANY ((ARRAY['operator'::character varying, 'system'::character varying, 'import'::character varying, 'ai_job'::character varying])::text[]))),
    CONSTRAINT ck_intelligence_calendar_occurrence_schedule_revisions__1e22 CHECK (((date_precision)::text = ANY ((ARRAY['exact'::character varying, 'range'::character varying, 'month'::character varying, 'quarter'::character varying, 'year'::character varying, 'approximate'::character varying, 'unknown'::character varying])::text[]))),
    CONSTRAINT ck_intelligence_calendar_occurrence_schedule_revisions__2686 CHECK (((((temporal_mode)::text = 'date'::text) AND ((time_precision)::text = 'not_applicable'::text)) OR ((temporal_mode)::text <> 'date'::text))),
    CONSTRAINT ck_intelligence_calendar_occurrence_schedule_revisions__4862 CHECK (((time_precision)::text = ANY ((ARRAY['exact'::character varying, 'approximate'::character varying, 'part_of_day'::character varying, 'unknown'::character varying, 'not_applicable'::character varying])::text[]))),
    CONSTRAINT ck_intelligence_calendar_occurrence_schedule_revisions__5417 CHECK (((temporal_mode)::text = ANY ((ARRAY['timed'::character varying, 'date'::character varying, 'unknown'::character varying])::text[]))),
    CONSTRAINT ck_intelligence_calendar_occurrence_schedule_revisions__a151 CHECK (((((temporal_mode)::text = 'timed'::text) AND (scheduled_start_at IS NOT NULL) AND (start_date IS NULL) AND (end_date_exclusive IS NULL) AND (timezone_name IS NOT NULL) AND (NOT all_day)) OR (((temporal_mode)::text = 'date'::text) AND (scheduled_start_at IS NULL) AND (scheduled_end_at IS NULL) AND (start_date IS NOT NULL) AND (end_date_exclusive IS NOT NULL) AND all_day) OR (((temporal_mode)::text = 'unknown'::text) AND (scheduled_start_at IS NULL) AND (scheduled_end_at IS NULL) AND (start_date IS NULL) AND (end_date_exclusive IS NULL) AND (NOT all_day)))),
    CONSTRAINT ck_intelligence_calendar_occurrence_schedule_revisions__aaff CHECK (((scheduled_end_at IS NULL) OR (scheduled_end_at > scheduled_start_at))),
    CONSTRAINT ck_intelligence_calendar_occurrence_schedule_revisions__bc1f CHECK ((revision_number > 0)),
    CONSTRAINT ck_intelligence_calendar_occurrence_schedule_revisions__d8bc CHECK (((end_date_exclusive IS NULL) OR (end_date_exclusive > start_date)))
);


--
-- Name: intelligence_calendar_occurrence_schedule_revisions_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.intelligence_calendar_occurrence_schedule_revisions_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: intelligence_calendar_occurrence_schedule_revisions_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.intelligence_calendar_occurrence_schedule_revisions_id_seq OWNED BY public.intelligence_calendar_occurrence_schedule_revisions.id;


--
-- Name: intelligence_calendar_policy_content_formats; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.intelligence_calendar_policy_content_formats (
    policy_id bigint NOT NULL,
    content_format_slug character varying(50) NOT NULL,
    actor_kind character varying(20) DEFAULT 'operator'::character varying NOT NULL,
    actor_ref character varying(255),
    actor_label character varying(255),
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    CONSTRAINT ck_intelligence_calendar_policy_content_formats_actor_kind CHECK (((actor_kind)::text = ANY ((ARRAY['operator'::character varying, 'system'::character varying, 'import'::character varying, 'ai_job'::character varying])::text[])))
);


--
-- Name: intelligence_calendar_policy_document_types; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.intelligence_calendar_policy_document_types (
    policy_id bigint NOT NULL,
    document_type_id bigint NOT NULL,
    include_descendants boolean DEFAULT false NOT NULL,
    actor_kind character varying(20) DEFAULT 'operator'::character varying NOT NULL,
    actor_ref character varying(255),
    actor_label character varying(255),
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    CONSTRAINT ck_intelligence_calendar_policy_document_types_actor_kind CHECK (((actor_kind)::text = ANY ((ARRAY['operator'::character varying, 'system'::character varying, 'import'::character varying, 'ai_job'::character varying])::text[])))
);


--
-- Name: intelligence_calendar_policy_search_terms; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.intelligence_calendar_policy_search_terms (
    id bigint NOT NULL,
    policy_id bigint NOT NULL,
    term character varying(500) NOT NULL,
    language_tag character varying(255) NOT NULL,
    term_type character varying(30) NOT NULL,
    weight numeric(5,2) DEFAULT 1 NOT NULL,
    actor_kind character varying(20) DEFAULT 'operator'::character varying NOT NULL,
    actor_ref character varying(255),
    actor_label character varying(255),
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    CONSTRAINT ck_intelligence_calendar_policy_search_terms_actor_kind CHECK (((actor_kind)::text = ANY ((ARRAY['operator'::character varying, 'system'::character varying, 'import'::character varying, 'ai_job'::character varying])::text[]))),
    CONSTRAINT ck_intelligence_calendar_policy_search_terms_term_nonempty CHECK ((btrim((term)::text) <> ''::text)),
    CONSTRAINT ck_intelligence_calendar_policy_search_terms_term_type CHECK (((term_type)::text = ANY ((ARRAY['keyword'::character varying, 'exact_phrase'::character varying, 'regex'::character varying, 'entity_alias'::character varying, 'topic_term'::character varying, 'semantic_query'::character varying])::text[]))),
    CONSTRAINT ck_intelligence_calendar_policy_search_terms_weight CHECK (((weight > (0)::numeric) AND (weight <= (10)::numeric)))
);


--
-- Name: intelligence_calendar_policy_search_terms_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.intelligence_calendar_policy_search_terms_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: intelligence_calendar_policy_search_terms_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.intelligence_calendar_policy_search_terms_id_seq OWNED BY public.intelligence_calendar_policy_search_terms.id;


--
-- Name: intelligence_calendar_policy_watch_sources; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.intelligence_calendar_policy_watch_sources (
    id bigint NOT NULL,
    policy_id bigint NOT NULL,
    source_id bigint NOT NULL,
    source_endpoint_id bigint,
    purpose character varying(50) NOT NULL,
    polling_priority character varying(20) DEFAULT 'normal'::character varying NOT NULL,
    activation_at timestamp with time zone,
    deactivation_at timestamp with time zone,
    actor_kind character varying(20) DEFAULT 'operator'::character varying NOT NULL,
    actor_ref character varying(255),
    actor_label character varying(255),
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    CONSTRAINT ck_intelligence_calendar_policy_watch_sources_activatio_99de CHECK (((deactivation_at IS NULL) OR (deactivation_at > activation_at))),
    CONSTRAINT ck_intelligence_calendar_policy_watch_sources_actor_kind CHECK (((actor_kind)::text = ANY ((ARRAY['operator'::character varying, 'system'::character varying, 'import'::character varying, 'ai_job'::character varying])::text[]))),
    CONSTRAINT ck_intelligence_calendar_policy_watch_sources_polling_priority CHECK (((polling_priority)::text = ANY ((ARRAY['low'::character varying, 'normal'::character varying, 'high'::character varying, 'critical'::character varying])::text[])))
);


--
-- Name: intelligence_calendar_policy_watch_sources_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.intelligence_calendar_policy_watch_sources_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: intelligence_calendar_policy_watch_sources_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.intelligence_calendar_policy_watch_sources_id_seq OWNED BY public.intelligence_calendar_policy_watch_sources.id;


--
-- Name: language_tag_aliases; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.language_tag_aliases (
    alias_key character varying(255) NOT NULL,
    alias character varying(255) NOT NULL,
    canonical_tag character varying(255) NOT NULL,
    alias_type character varying(50) NOT NULL,
    is_active boolean DEFAULT true NOT NULL,
    metadata jsonb DEFAULT '{}'::jsonb NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL
);


--
-- Name: language_tags; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.language_tags (
    tag character varying(255) NOT NULL,
    language_subtag character varying(8),
    script_subtag character varying(4),
    region_subtag character varying(3),
    is_private_use boolean DEFAULT false NOT NULL,
    is_active boolean DEFAULT true NOT NULL,
    metadata jsonb DEFAULT '{}'::jsonb NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL
);


--
-- Name: monitor_alert_destinations; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.monitor_alert_destinations (
    monitor_id bigint NOT NULL,
    destination_id bigint NOT NULL,
    is_enabled boolean DEFAULT true NOT NULL,
    priority character varying(20),
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL,
    CONSTRAINT ck_monitor_alert_destinations_priority CHECK (((priority IS NULL) OR ((priority)::text = ANY ((ARRAY['low'::character varying, 'normal'::character varying, 'high'::character varying, 'critical'::character varying])::text[]))))
);


--
-- Name: monitor_evaluation_runs; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.monitor_evaluation_runs (
    id bigint NOT NULL,
    monitor_id bigint NOT NULL,
    monitor_revision_id bigint NOT NULL,
    document_id bigint,
    trigger_type character varying(30) NOT NULL,
    status character varying(20) DEFAULT 'running'::character varying NOT NULL,
    started_at timestamp with time zone DEFAULT now() NOT NULL,
    completed_at timestamp with time zone,
    candidate_count integer DEFAULT 0 NOT NULL,
    matched_count integer DEFAULT 0 NOT NULL,
    new_match_count integer DEFAULT 0 NOT NULL,
    error text,
    metadata jsonb DEFAULT '{}'::jsonb NOT NULL,
    CONSTRAINT ck_monitor_evaluation_runs_completed_after_started CHECK (((completed_at IS NULL) OR (completed_at >= started_at))),
    CONSTRAINT ck_monitor_evaluation_runs_completion_state CHECK (((((status)::text = 'running'::text) AND (completed_at IS NULL)) OR (((status)::text <> 'running'::text) AND (completed_at IS NOT NULL)))),
    CONSTRAINT ck_monitor_evaluation_runs_count_order CHECK (((matched_count <= candidate_count) AND (new_match_count <= matched_count))),
    CONSTRAINT ck_monitor_evaluation_runs_counts_nonnegative CHECK (((candidate_count >= 0) AND (matched_count >= 0) AND (new_match_count >= 0))),
    CONSTRAINT ck_monitor_evaluation_runs_status CHECK (((status)::text = ANY ((ARRAY['running'::character varying, 'succeeded'::character varying, 'failed'::character varying])::text[]))),
    CONSTRAINT ck_monitor_evaluation_runs_trigger_type CHECK (((trigger_type)::text = ANY ((ARRAY['activation_backfill'::character varying, 'manual_backfill'::character varying, 'manual_document'::character varying, 'ingestion'::character varying, 'enrichment'::character varying])::text[])))
);


--
-- Name: monitor_evaluation_runs_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.monitor_evaluation_runs_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: monitor_evaluation_runs_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.monitor_evaluation_runs_id_seq OWNED BY public.monitor_evaluation_runs.id;


--
-- Name: monitor_matches; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.monitor_matches (
    id bigint NOT NULL,
    monitor_id bigint NOT NULL,
    document_id bigint NOT NULL,
    first_monitor_revision_id bigint NOT NULL,
    last_monitor_revision_id bigint NOT NULL,
    first_evaluation_run_id bigint,
    last_evaluation_run_id bigint,
    first_matched_at timestamp with time zone DEFAULT now() NOT NULL,
    last_matched_at timestamp with time zone DEFAULT now() NOT NULL,
    observation_count integer DEFAULT 1 NOT NULL,
    CONSTRAINT ck_monitor_matches_last_after_first CHECK ((last_matched_at >= first_matched_at)),
    CONSTRAINT ck_monitor_matches_observation_count_positive CHECK ((observation_count > 0))
);


--
-- Name: monitor_matches_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.monitor_matches_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: monitor_matches_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.monitor_matches_id_seq OWNED BY public.monitor_matches.id;


--
-- Name: monitor_revision_content_formats; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.monitor_revision_content_formats (
    revision_id bigint NOT NULL,
    content_format_slug character varying(50) NOT NULL
);


--
-- Name: monitor_revision_document_types; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.monitor_revision_document_types (
    revision_id bigint NOT NULL,
    document_type_id bigint NOT NULL,
    include_descendants boolean DEFAULT false NOT NULL
);


--
-- Name: monitor_revision_entities; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.monitor_revision_entities (
    revision_id bigint NOT NULL,
    entity_id bigint NOT NULL
);


--
-- Name: monitor_revision_entity_roles; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.monitor_revision_entity_roles (
    revision_id bigint NOT NULL,
    entity_role character varying(50) NOT NULL,
    CONSTRAINT ck_monitor_revision_entity_roles_entity_role_nonempty CHECK ((btrim((entity_role)::text) <> ''::text))
);


--
-- Name: monitor_revision_geographies; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.monitor_revision_geographies (
    revision_id bigint NOT NULL,
    geography_id bigint NOT NULL,
    include_descendants boolean DEFAULT false NOT NULL
);


--
-- Name: monitor_revision_languages; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.monitor_revision_languages (
    revision_id bigint NOT NULL,
    language_tag character varying(255) NOT NULL
);


--
-- Name: monitor_revision_source_types; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.monitor_revision_source_types (
    revision_id bigint NOT NULL,
    source_type_slug character varying(50) NOT NULL,
    include_descendants boolean DEFAULT false NOT NULL
);


--
-- Name: monitor_revision_sources; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.monitor_revision_sources (
    revision_id bigint NOT NULL,
    source_id bigint NOT NULL
);


--
-- Name: monitor_revision_topics; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.monitor_revision_topics (
    revision_id bigint NOT NULL,
    topic_id bigint NOT NULL,
    include_descendants boolean DEFAULT false NOT NULL
);


--
-- Name: monitor_revisions; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.monitor_revisions (
    id bigint NOT NULL,
    monitor_id bigint NOT NULL,
    revision_number integer NOT NULL,
    criteria_version integer DEFAULT 1 NOT NULL,
    minimum_confidence numeric(5,4),
    effective_from timestamp with time zone,
    text_query text,
    match_all_in_profile boolean DEFAULT false NOT NULL,
    change_reason text,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    sealed_at timestamp with time zone,
    CONSTRAINT ck_monitor_revisions_criteria_version CHECK ((criteria_version = 1)),
    CONSTRAINT ck_monitor_revisions_minimum_confidence_range CHECK (((minimum_confidence IS NULL) OR ((minimum_confidence >= (0)::numeric) AND (minimum_confidence <= (1)::numeric)))),
    CONSTRAINT ck_monitor_revisions_revision_positive CHECK ((revision_number > 0)),
    CONSTRAINT ck_monitor_revisions_text_query CHECK (((text_query IS NULL) OR ((btrim(text_query) <> ''::text) AND (length(text_query) <= 500))))
);


--
-- Name: monitor_revisions_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.monitor_revisions_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: monitor_revisions_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.monitor_revisions_id_seq OWNED BY public.monitor_revisions.id;


--
-- Name: monitors; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.monitors (
    id bigint NOT NULL,
    slug character varying(255) NOT NULL,
    name character varying(255) NOT NULL,
    description text,
    coverage_profile_id bigint NOT NULL,
    status character varying(20) DEFAULT 'draft'::character varying NOT NULL,
    current_revision_number integer DEFAULT 1 NOT NULL,
    match_existing_on_activation boolean DEFAULT false NOT NULL,
    expires_at timestamp with time zone,
    activated_at timestamp with time zone,
    paused_at timestamp with time zone,
    expired_at timestamp with time zone,
    archived_at timestamp with time zone,
    metadata jsonb DEFAULT '{}'::jsonb NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL,
    CONSTRAINT ck_monitors_active_timestamp CHECK ((((status)::text <> 'active'::text) OR (activated_at IS NOT NULL))),
    CONSTRAINT ck_monitors_archived_timestamp CHECK ((((status)::text <> 'archived'::text) OR (archived_at IS NOT NULL))),
    CONSTRAINT ck_monitors_current_revision_positive CHECK ((current_revision_number > 0)),
    CONSTRAINT ck_monitors_expired_timestamp CHECK ((((status)::text <> 'expired'::text) OR (expired_at IS NOT NULL))),
    CONSTRAINT ck_monitors_name_nonempty CHECK ((btrim((name)::text) <> ''::text)),
    CONSTRAINT ck_monitors_paused_timestamp CHECK ((((status)::text <> 'paused'::text) OR (paused_at IS NOT NULL))),
    CONSTRAINT ck_monitors_slug_format CHECK (((slug)::text ~ '^[a-z0-9]+(_[a-z0-9]+)*$'::text)),
    CONSTRAINT ck_monitors_status CHECK (((status)::text = ANY ((ARRAY['draft'::character varying, 'active'::character varying, 'paused'::character varying, 'expired'::character varying, 'archived'::character varying])::text[])))
);


--
-- Name: monitors_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.monitors_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: monitors_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.monitors_id_seq OWNED BY public.monitors.id;


--
-- Name: platforms; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.platforms (
    id bigint NOT NULL,
    slug character varying(50) NOT NULL,
    name character varying(100) NOT NULL,
    description text,
    is_active boolean DEFAULT true NOT NULL,
    metadata jsonb DEFAULT '{}'::jsonb NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL
);


--
-- Name: platforms_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.platforms_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: platforms_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.platforms_id_seq OWNED BY public.platforms.id;


--
-- Name: semantic_assignment_methods; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.semantic_assignment_methods (
    slug character varying(50) NOT NULL,
    name character varying(255) NOT NULL,
    description text,
    is_active boolean DEFAULT true NOT NULL,
    metadata jsonb DEFAULT '{}'::jsonb NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL
);


--
-- Name: semantic_mapping_relations; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.semantic_mapping_relations (
    slug character varying(50) NOT NULL,
    name character varying(255) NOT NULL,
    description text,
    relation_family character varying(20) NOT NULL,
    applicable_resource_kind character varying(50) NOT NULL,
    external_identifier character varying(100) NOT NULL,
    external_uri text NOT NULL,
    is_symmetric boolean NOT NULL,
    is_transitive boolean NOT NULL,
    inverse_slug character varying(50),
    is_active boolean DEFAULT true NOT NULL,
    metadata jsonb DEFAULT '{}'::jsonb NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL
);


--
-- Name: source_endpoints; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.source_endpoints (
    id bigint NOT NULL,
    source_id bigint NOT NULL,
    name character varying(255),
    endpoint_type character varying(50) NOT NULL,
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
    endpoint_format character varying(50) NOT NULL,
    acquisition_method character varying(50) NOT NULL,
    platform character varying(50),
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
-- Name: source_types; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.source_types (
    id bigint NOT NULL,
    parent_id bigint,
    slug character varying(50) NOT NULL,
    name character varying(100) NOT NULL,
    description text,
    is_active boolean DEFAULT true NOT NULL,
    metadata jsonb DEFAULT '{}'::jsonb NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL
);


--
-- Name: source_types_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.source_types_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: source_types_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.source_types_id_seq OWNED BY public.source_types.id;


--
-- Name: sources; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.sources (
    id bigint NOT NULL,
    name character varying(255) NOT NULL,
    native_name character varying(255),
    country character varying(100) NOT NULL,
    primary_language character varying(255) NOT NULL,
    source_type character varying(50) NOT NULL,
    status character varying(30) DEFAULT 'active'::character varying NOT NULL,
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
-- Name: topics; Type: TABLE; Schema: public; Owner: -
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


--
-- Name: topics_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.topics_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: topics_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.topics_id_seq OWNED BY public.topics.id;


--
-- Name: acquisition_methods id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.acquisition_methods ALTER COLUMN id SET DEFAULT nextval('public.acquisition_methods_id_seq'::regclass);


--
-- Name: alert_deliveries id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.alert_deliveries ALTER COLUMN id SET DEFAULT nextval('public.alert_deliveries_id_seq'::regclass);


--
-- Name: alert_delivery_attempts id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.alert_delivery_attempts ALTER COLUMN id SET DEFAULT nextval('public.alert_delivery_attempts_id_seq'::regclass);


--
-- Name: alert_destinations id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.alert_destinations ALTER COLUMN id SET DEFAULT nextval('public.alert_destinations_id_seq'::regclass);


--
-- Name: alerts id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.alerts ALTER COLUMN id SET DEFAULT nextval('public.alerts_id_seq'::regclass);


--
-- Name: classification_runs id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.classification_runs ALTER COLUMN id SET DEFAULT nextval('public.classification_runs_id_seq'::regclass);


--
-- Name: content_formats id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.content_formats ALTER COLUMN id SET DEFAULT nextval('public.content_formats_id_seq'::regclass);


--
-- Name: coverage_profiles id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.coverage_profiles ALTER COLUMN id SET DEFAULT nextval('public.coverage_profiles_id_seq'::regclass);


--
-- Name: document_entities id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.document_entities ALTER COLUMN id SET DEFAULT nextval('public.document_entities_id_seq'::regclass);


--
-- Name: document_geographies id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.document_geographies ALTER COLUMN id SET DEFAULT nextval('public.document_geographies_id_seq'::regclass);


--
-- Name: document_topics id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.document_topics ALTER COLUMN id SET DEFAULT nextval('public.document_topics_id_seq'::regclass);


--
-- Name: document_type_assignments id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.document_type_assignments ALTER COLUMN id SET DEFAULT nextval('public.document_type_assignments_id_seq'::regclass);


--
-- Name: document_types id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.document_types ALTER COLUMN id SET DEFAULT nextval('public.document_types_id_seq'::regclass);


--
-- Name: document_versions id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.document_versions ALTER COLUMN id SET DEFAULT nextval('public.document_versions_id_seq'::regclass);


--
-- Name: documents id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.documents ALTER COLUMN id SET DEFAULT nextval('public.documents_id_seq'::regclass);


--
-- Name: endpoint_formats id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.endpoint_formats ALTER COLUMN id SET DEFAULT nextval('public.endpoint_formats_id_seq'::regclass);


--
-- Name: endpoint_types id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.endpoint_types ALTER COLUMN id SET DEFAULT nextval('public.endpoint_types_id_seq'::regclass);


--
-- Name: entities id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.entities ALTER COLUMN id SET DEFAULT nextval('public.entities_id_seq'::regclass);


--
-- Name: entity_aliases id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.entity_aliases ALTER COLUMN id SET DEFAULT nextval('public.entity_aliases_id_seq'::regclass);


--
-- Name: entity_geographies id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.entity_geographies ALTER COLUMN id SET DEFAULT nextval('public.entity_geographies_id_seq'::regclass);


--
-- Name: entity_geography_relationship_type_external_mappings id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.entity_geography_relationship_type_external_mappings ALTER COLUMN id SET DEFAULT nextval('public.entity_geography_relationship_type_external_mappings_id_seq'::regclass);


--
-- Name: entity_type_assignments id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.entity_type_assignments ALTER COLUMN id SET DEFAULT nextval('public.entity_type_assignments_id_seq'::regclass);


--
-- Name: entity_type_external_mappings id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.entity_type_external_mappings ALTER COLUMN id SET DEFAULT nextval('public.entity_type_external_mappings_id_seq'::regclass);


--
-- Name: entity_type_hierarchy_edges id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.entity_type_hierarchy_edges ALTER COLUMN id SET DEFAULT nextval('public.entity_type_hierarchy_edges_id_seq'::regclass);


--
-- Name: entity_types id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.entity_types ALTER COLUMN id SET DEFAULT nextval('public.entity_types_id_seq'::regclass);


--
-- Name: external_semantic_resources id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.external_semantic_resources ALTER COLUMN id SET DEFAULT nextval('public.external_semantic_resources_id_seq'::regclass);


--
-- Name: external_semantic_schemes id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.external_semantic_schemes ALTER COLUMN id SET DEFAULT nextval('public.external_semantic_schemes_id_seq'::regclass);


--
-- Name: geographies id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.geographies ALTER COLUMN id SET DEFAULT nextval('public.geographies_id_seq'::regclass);


--
-- Name: ingestion_runs id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.ingestion_runs ALTER COLUMN id SET DEFAULT nextval('public.ingestion_runs_id_seq'::regclass);


--
-- Name: intelligence_calendar_event_aliases id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.intelligence_calendar_event_aliases ALTER COLUMN id SET DEFAULT nextval('public.intelligence_calendar_event_aliases_id_seq'::regclass);


--
-- Name: intelligence_calendar_event_coverage_policies id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.intelligence_calendar_event_coverage_policies ALTER COLUMN id SET DEFAULT nextval('public.intelligence_calendar_event_coverage_policies_id_seq'::regclass);


--
-- Name: intelligence_calendar_event_documents id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.intelligence_calendar_event_documents ALTER COLUMN id SET DEFAULT nextval('public.intelligence_calendar_event_documents_id_seq'::regclass);


--
-- Name: intelligence_calendar_event_entities id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.intelligence_calendar_event_entities ALTER COLUMN id SET DEFAULT nextval('public.intelligence_calendar_event_entities_id_seq'::regclass);


--
-- Name: intelligence_calendar_event_evidence id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.intelligence_calendar_event_evidence ALTER COLUMN id SET DEFAULT nextval('public.intelligence_calendar_event_evidence_id_seq'::regclass);


--
-- Name: intelligence_calendar_event_geographies id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.intelligence_calendar_event_geographies ALTER COLUMN id SET DEFAULT nextval('public.intelligence_calendar_event_geographies_id_seq'::regclass);


--
-- Name: intelligence_calendar_event_merge_history id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.intelligence_calendar_event_merge_history ALTER COLUMN id SET DEFAULT nextval('public.intelligence_calendar_event_merge_history_id_seq'::regclass);


--
-- Name: intelligence_calendar_event_monitors id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.intelligence_calendar_event_monitors ALTER COLUMN id SET DEFAULT nextval('public.intelligence_calendar_event_monitors_id_seq'::regclass);


--
-- Name: intelligence_calendar_event_occurrences id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.intelligence_calendar_event_occurrences ALTER COLUMN id SET DEFAULT nextval('public.intelligence_calendar_event_occurrences_id_seq'::regclass);


--
-- Name: intelligence_calendar_event_recurrence_exceptions id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.intelligence_calendar_event_recurrence_exceptions ALTER COLUMN id SET DEFAULT nextval('public.intelligence_calendar_event_recurrence_exceptions_id_seq'::regclass);


--
-- Name: intelligence_calendar_event_recurrence_rules id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.intelligence_calendar_event_recurrence_rules ALTER COLUMN id SET DEFAULT nextval('public.intelligence_calendar_event_recurrence_rules_id_seq'::regclass);


--
-- Name: intelligence_calendar_event_revisions id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.intelligence_calendar_event_revisions ALTER COLUMN id SET DEFAULT nextval('public.intelligence_calendar_event_revisions_id_seq'::regclass);


--
-- Name: intelligence_calendar_event_sources id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.intelligence_calendar_event_sources ALTER COLUMN id SET DEFAULT nextval('public.intelligence_calendar_event_sources_id_seq'::regclass);


--
-- Name: intelligence_calendar_event_state_transitions id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.intelligence_calendar_event_state_transitions ALTER COLUMN id SET DEFAULT nextval('public.intelligence_calendar_event_state_transitions_id_seq'::regclass);


--
-- Name: intelligence_calendar_event_topics id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.intelligence_calendar_event_topics ALTER COLUMN id SET DEFAULT nextval('public.intelligence_calendar_event_topics_id_seq'::regclass);


--
-- Name: intelligence_calendar_events id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.intelligence_calendar_events ALTER COLUMN id SET DEFAULT nextval('public.intelligence_calendar_events_id_seq'::regclass);


--
-- Name: intelligence_calendar_occurrence_policy_overrides id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.intelligence_calendar_occurrence_policy_overrides ALTER COLUMN id SET DEFAULT nextval('public.intelligence_calendar_occurrence_policy_overrides_id_seq'::regclass);


--
-- Name: intelligence_calendar_occurrence_schedule_revisions id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.intelligence_calendar_occurrence_schedule_revisions ALTER COLUMN id SET DEFAULT nextval('public.intelligence_calendar_occurrence_schedule_revisions_id_seq'::regclass);


--
-- Name: intelligence_calendar_policy_search_terms id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.intelligence_calendar_policy_search_terms ALTER COLUMN id SET DEFAULT nextval('public.intelligence_calendar_policy_search_terms_id_seq'::regclass);


--
-- Name: intelligence_calendar_policy_watch_sources id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.intelligence_calendar_policy_watch_sources ALTER COLUMN id SET DEFAULT nextval('public.intelligence_calendar_policy_watch_sources_id_seq'::regclass);


--
-- Name: monitor_evaluation_runs id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.monitor_evaluation_runs ALTER COLUMN id SET DEFAULT nextval('public.monitor_evaluation_runs_id_seq'::regclass);


--
-- Name: monitor_matches id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.monitor_matches ALTER COLUMN id SET DEFAULT nextval('public.monitor_matches_id_seq'::regclass);


--
-- Name: monitor_revisions id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.monitor_revisions ALTER COLUMN id SET DEFAULT nextval('public.monitor_revisions_id_seq'::regclass);


--
-- Name: monitors id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.monitors ALTER COLUMN id SET DEFAULT nextval('public.monitors_id_seq'::regclass);


--
-- Name: platforms id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.platforms ALTER COLUMN id SET DEFAULT nextval('public.platforms_id_seq'::regclass);


--
-- Name: source_endpoints id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.source_endpoints ALTER COLUMN id SET DEFAULT nextval('public.source_endpoints_id_seq'::regclass);


--
-- Name: source_types id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.source_types ALTER COLUMN id SET DEFAULT nextval('public.source_types_id_seq'::regclass);


--
-- Name: sources id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.sources ALTER COLUMN id SET DEFAULT nextval('public.sources_id_seq'::regclass);


--
-- Name: topics id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.topics ALTER COLUMN id SET DEFAULT nextval('public.topics_id_seq'::regclass);


--
-- Name: alembic_version alembic_version_pkc; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.alembic_version
    ADD CONSTRAINT alembic_version_pkc PRIMARY KEY (version_num);


--
-- Name: acquisition_methods pk_acquisition_methods; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.acquisition_methods
    ADD CONSTRAINT pk_acquisition_methods PRIMARY KEY (id);


--
-- Name: alert_deliveries pk_alert_deliveries; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.alert_deliveries
    ADD CONSTRAINT pk_alert_deliveries PRIMARY KEY (id);


--
-- Name: alert_delivery_attempts pk_alert_delivery_attempts; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.alert_delivery_attempts
    ADD CONSTRAINT pk_alert_delivery_attempts PRIMARY KEY (id);


--
-- Name: alert_destinations pk_alert_destinations; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.alert_destinations
    ADD CONSTRAINT pk_alert_destinations PRIMARY KEY (id);


--
-- Name: alerts pk_alerts; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.alerts
    ADD CONSTRAINT pk_alerts PRIMARY KEY (id);


--
-- Name: classification_runs pk_classification_runs; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.classification_runs
    ADD CONSTRAINT pk_classification_runs PRIMARY KEY (id);


--
-- Name: content_formats pk_content_formats; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.content_formats
    ADD CONSTRAINT pk_content_formats PRIMARY KEY (id);


--
-- Name: coverage_profile_content_formats pk_coverage_profile_content_formats; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.coverage_profile_content_formats
    ADD CONSTRAINT pk_coverage_profile_content_formats PRIMARY KEY (profile_id, content_format_slug);


--
-- Name: coverage_profile_document_types pk_coverage_profile_document_types; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.coverage_profile_document_types
    ADD CONSTRAINT pk_coverage_profile_document_types PRIMARY KEY (profile_id, document_type_id);


--
-- Name: coverage_profile_geographies pk_coverage_profile_geographies; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.coverage_profile_geographies
    ADD CONSTRAINT pk_coverage_profile_geographies PRIMARY KEY (profile_id, geography_id);


--
-- Name: coverage_profile_languages pk_coverage_profile_languages; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.coverage_profile_languages
    ADD CONSTRAINT pk_coverage_profile_languages PRIMARY KEY (profile_id, language_tag);


--
-- Name: coverage_profile_source_polling_overrides pk_coverage_profile_source_polling_overrides; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.coverage_profile_source_polling_overrides
    ADD CONSTRAINT pk_coverage_profile_source_polling_overrides PRIMARY KEY (profile_id, source_id);


--
-- Name: coverage_profile_source_types pk_coverage_profile_source_types; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.coverage_profile_source_types
    ADD CONSTRAINT pk_coverage_profile_source_types PRIMARY KEY (profile_id, source_type_slug);


--
-- Name: coverage_profile_sources pk_coverage_profile_sources; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.coverage_profile_sources
    ADD CONSTRAINT pk_coverage_profile_sources PRIMARY KEY (profile_id, source_id);


--
-- Name: coverage_profile_topics pk_coverage_profile_topics; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.coverage_profile_topics
    ADD CONSTRAINT pk_coverage_profile_topics PRIMARY KEY (profile_id, topic_id);


--
-- Name: coverage_profile_translation_targets pk_coverage_profile_translation_targets; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.coverage_profile_translation_targets
    ADD CONSTRAINT pk_coverage_profile_translation_targets PRIMARY KEY (profile_id, language_tag);


--
-- Name: coverage_profiles pk_coverage_profiles; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.coverage_profiles
    ADD CONSTRAINT pk_coverage_profiles PRIMARY KEY (id);


--
-- Name: document_entities pk_document_entities; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.document_entities
    ADD CONSTRAINT pk_document_entities PRIMARY KEY (id);


--
-- Name: document_geographies pk_document_geographies; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.document_geographies
    ADD CONSTRAINT pk_document_geographies PRIMARY KEY (id);


--
-- Name: document_topics pk_document_topics; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.document_topics
    ADD CONSTRAINT pk_document_topics PRIMARY KEY (id);


--
-- Name: document_type_assignments pk_document_type_assignments; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.document_type_assignments
    ADD CONSTRAINT pk_document_type_assignments PRIMARY KEY (id);


--
-- Name: document_types pk_document_types; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.document_types
    ADD CONSTRAINT pk_document_types PRIMARY KEY (id);


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
-- Name: endpoint_formats pk_endpoint_formats; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.endpoint_formats
    ADD CONSTRAINT pk_endpoint_formats PRIMARY KEY (id);


--
-- Name: endpoint_types pk_endpoint_types; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.endpoint_types
    ADD CONSTRAINT pk_endpoint_types PRIMARY KEY (id);


--
-- Name: entities pk_entities; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.entities
    ADD CONSTRAINT pk_entities PRIMARY KEY (id);


--
-- Name: entity_aliases pk_entity_aliases; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.entity_aliases
    ADD CONSTRAINT pk_entity_aliases PRIMARY KEY (id);


--
-- Name: entity_geographies pk_entity_geographies; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.entity_geographies
    ADD CONSTRAINT pk_entity_geographies PRIMARY KEY (id);


--
-- Name: entity_geography_relationship_type_external_mappings pk_entity_geography_relationship_type_external_mappings; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.entity_geography_relationship_type_external_mappings
    ADD CONSTRAINT pk_entity_geography_relationship_type_external_mappings PRIMARY KEY (id);


--
-- Name: entity_geography_relationship_types pk_entity_geography_relationship_types; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.entity_geography_relationship_types
    ADD CONSTRAINT pk_entity_geography_relationship_types PRIMARY KEY (slug);


--
-- Name: entity_type_assignments pk_entity_type_assignments; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.entity_type_assignments
    ADD CONSTRAINT pk_entity_type_assignments PRIMARY KEY (id);


--
-- Name: entity_type_external_mappings pk_entity_type_external_mappings; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.entity_type_external_mappings
    ADD CONSTRAINT pk_entity_type_external_mappings PRIMARY KEY (id);


--
-- Name: entity_type_hierarchy_edges pk_entity_type_hierarchy_edges; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.entity_type_hierarchy_edges
    ADD CONSTRAINT pk_entity_type_hierarchy_edges PRIMARY KEY (id);


--
-- Name: entity_types pk_entity_types; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.entity_types
    ADD CONSTRAINT pk_entity_types PRIMARY KEY (id);


--
-- Name: external_semantic_authorities pk_external_semantic_authorities; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.external_semantic_authorities
    ADD CONSTRAINT pk_external_semantic_authorities PRIMARY KEY (slug);


--
-- Name: external_semantic_resource_kinds pk_external_semantic_resource_kinds; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.external_semantic_resource_kinds
    ADD CONSTRAINT pk_external_semantic_resource_kinds PRIMARY KEY (slug);


--
-- Name: external_semantic_resources pk_external_semantic_resources; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.external_semantic_resources
    ADD CONSTRAINT pk_external_semantic_resources PRIMARY KEY (id);


--
-- Name: external_semantic_schemes pk_external_semantic_schemes; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.external_semantic_schemes
    ADD CONSTRAINT pk_external_semantic_schemes PRIMARY KEY (id);


--
-- Name: geographies pk_geographies; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.geographies
    ADD CONSTRAINT pk_geographies PRIMARY KEY (id);


--
-- Name: ingestion_runs pk_ingestion_runs; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.ingestion_runs
    ADD CONSTRAINT pk_ingestion_runs PRIMARY KEY (id);


--
-- Name: intelligence_calendar_event_aliases pk_intelligence_calendar_event_aliases; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.intelligence_calendar_event_aliases
    ADD CONSTRAINT pk_intelligence_calendar_event_aliases PRIMARY KEY (id);


--
-- Name: intelligence_calendar_event_coverage_policies pk_intelligence_calendar_event_coverage_policies; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.intelligence_calendar_event_coverage_policies
    ADD CONSTRAINT pk_intelligence_calendar_event_coverage_policies PRIMARY KEY (id);


--
-- Name: intelligence_calendar_event_documents pk_intelligence_calendar_event_documents; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.intelligence_calendar_event_documents
    ADD CONSTRAINT pk_intelligence_calendar_event_documents PRIMARY KEY (id);


--
-- Name: intelligence_calendar_event_entities pk_intelligence_calendar_event_entities; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.intelligence_calendar_event_entities
    ADD CONSTRAINT pk_intelligence_calendar_event_entities PRIMARY KEY (id);


--
-- Name: intelligence_calendar_event_evidence pk_intelligence_calendar_event_evidence; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.intelligence_calendar_event_evidence
    ADD CONSTRAINT pk_intelligence_calendar_event_evidence PRIMARY KEY (id);


--
-- Name: intelligence_calendar_event_geographies pk_intelligence_calendar_event_geographies; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.intelligence_calendar_event_geographies
    ADD CONSTRAINT pk_intelligence_calendar_event_geographies PRIMARY KEY (id);


--
-- Name: intelligence_calendar_event_merge_history pk_intelligence_calendar_event_merge_history; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.intelligence_calendar_event_merge_history
    ADD CONSTRAINT pk_intelligence_calendar_event_merge_history PRIMARY KEY (id);


--
-- Name: intelligence_calendar_event_monitors pk_intelligence_calendar_event_monitors; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.intelligence_calendar_event_monitors
    ADD CONSTRAINT pk_intelligence_calendar_event_monitors PRIMARY KEY (id);


--
-- Name: intelligence_calendar_event_occurrences pk_intelligence_calendar_event_occurrences; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.intelligence_calendar_event_occurrences
    ADD CONSTRAINT pk_intelligence_calendar_event_occurrences PRIMARY KEY (id);


--
-- Name: intelligence_calendar_event_recurrence_exceptions pk_intelligence_calendar_event_recurrence_exceptions; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.intelligence_calendar_event_recurrence_exceptions
    ADD CONSTRAINT pk_intelligence_calendar_event_recurrence_exceptions PRIMARY KEY (id);


--
-- Name: intelligence_calendar_event_recurrence_rules pk_intelligence_calendar_event_recurrence_rules; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.intelligence_calendar_event_recurrence_rules
    ADD CONSTRAINT pk_intelligence_calendar_event_recurrence_rules PRIMARY KEY (id);


--
-- Name: intelligence_calendar_event_revisions pk_intelligence_calendar_event_revisions; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.intelligence_calendar_event_revisions
    ADD CONSTRAINT pk_intelligence_calendar_event_revisions PRIMARY KEY (id);


--
-- Name: intelligence_calendar_event_sources pk_intelligence_calendar_event_sources; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.intelligence_calendar_event_sources
    ADD CONSTRAINT pk_intelligence_calendar_event_sources PRIMARY KEY (id);


--
-- Name: intelligence_calendar_event_state_transitions pk_intelligence_calendar_event_state_transitions; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.intelligence_calendar_event_state_transitions
    ADD CONSTRAINT pk_intelligence_calendar_event_state_transitions PRIMARY KEY (id);


--
-- Name: intelligence_calendar_event_topics pk_intelligence_calendar_event_topics; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.intelligence_calendar_event_topics
    ADD CONSTRAINT pk_intelligence_calendar_event_topics PRIMARY KEY (id);


--
-- Name: intelligence_calendar_events pk_intelligence_calendar_events; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.intelligence_calendar_events
    ADD CONSTRAINT pk_intelligence_calendar_events PRIMARY KEY (id);


--
-- Name: intelligence_calendar_occurrence_policy_overrides pk_intelligence_calendar_occurrence_policy_overrides; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.intelligence_calendar_occurrence_policy_overrides
    ADD CONSTRAINT pk_intelligence_calendar_occurrence_policy_overrides PRIMARY KEY (id);


--
-- Name: intelligence_calendar_occurrence_schedule_revisions pk_intelligence_calendar_occurrence_schedule_revisions; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.intelligence_calendar_occurrence_schedule_revisions
    ADD CONSTRAINT pk_intelligence_calendar_occurrence_schedule_revisions PRIMARY KEY (id);


--
-- Name: intelligence_calendar_policy_content_formats pk_intelligence_calendar_policy_content_formats; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.intelligence_calendar_policy_content_formats
    ADD CONSTRAINT pk_intelligence_calendar_policy_content_formats PRIMARY KEY (policy_id, content_format_slug);


--
-- Name: intelligence_calendar_policy_document_types pk_intelligence_calendar_policy_document_types; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.intelligence_calendar_policy_document_types
    ADD CONSTRAINT pk_intelligence_calendar_policy_document_types PRIMARY KEY (policy_id, document_type_id);


--
-- Name: intelligence_calendar_policy_search_terms pk_intelligence_calendar_policy_search_terms; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.intelligence_calendar_policy_search_terms
    ADD CONSTRAINT pk_intelligence_calendar_policy_search_terms PRIMARY KEY (id);


--
-- Name: intelligence_calendar_policy_watch_sources pk_intelligence_calendar_policy_watch_sources; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.intelligence_calendar_policy_watch_sources
    ADD CONSTRAINT pk_intelligence_calendar_policy_watch_sources PRIMARY KEY (id);


--
-- Name: language_tag_aliases pk_language_tag_aliases; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.language_tag_aliases
    ADD CONSTRAINT pk_language_tag_aliases PRIMARY KEY (alias_key);


--
-- Name: language_tags pk_language_tags; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.language_tags
    ADD CONSTRAINT pk_language_tags PRIMARY KEY (tag);


--
-- Name: monitor_alert_destinations pk_monitor_alert_destinations; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.monitor_alert_destinations
    ADD CONSTRAINT pk_monitor_alert_destinations PRIMARY KEY (monitor_id, destination_id);


--
-- Name: monitor_evaluation_runs pk_monitor_evaluation_runs; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.monitor_evaluation_runs
    ADD CONSTRAINT pk_monitor_evaluation_runs PRIMARY KEY (id);


--
-- Name: monitor_matches pk_monitor_matches; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.monitor_matches
    ADD CONSTRAINT pk_monitor_matches PRIMARY KEY (id);


--
-- Name: monitor_revision_content_formats pk_monitor_revision_content_formats; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.monitor_revision_content_formats
    ADD CONSTRAINT pk_monitor_revision_content_formats PRIMARY KEY (revision_id, content_format_slug);


--
-- Name: monitor_revision_document_types pk_monitor_revision_document_types; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.monitor_revision_document_types
    ADD CONSTRAINT pk_monitor_revision_document_types PRIMARY KEY (revision_id, document_type_id);


--
-- Name: monitor_revision_entities pk_monitor_revision_entities; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.monitor_revision_entities
    ADD CONSTRAINT pk_monitor_revision_entities PRIMARY KEY (revision_id, entity_id);


--
-- Name: monitor_revision_entity_roles pk_monitor_revision_entity_roles; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.monitor_revision_entity_roles
    ADD CONSTRAINT pk_monitor_revision_entity_roles PRIMARY KEY (revision_id, entity_role);


--
-- Name: monitor_revision_geographies pk_monitor_revision_geographies; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.monitor_revision_geographies
    ADD CONSTRAINT pk_monitor_revision_geographies PRIMARY KEY (revision_id, geography_id);


--
-- Name: monitor_revision_languages pk_monitor_revision_languages; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.monitor_revision_languages
    ADD CONSTRAINT pk_monitor_revision_languages PRIMARY KEY (revision_id, language_tag);


--
-- Name: monitor_revision_source_types pk_monitor_revision_source_types; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.monitor_revision_source_types
    ADD CONSTRAINT pk_monitor_revision_source_types PRIMARY KEY (revision_id, source_type_slug);


--
-- Name: monitor_revision_sources pk_monitor_revision_sources; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.monitor_revision_sources
    ADD CONSTRAINT pk_monitor_revision_sources PRIMARY KEY (revision_id, source_id);


--
-- Name: monitor_revision_topics pk_monitor_revision_topics; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.monitor_revision_topics
    ADD CONSTRAINT pk_monitor_revision_topics PRIMARY KEY (revision_id, topic_id);


--
-- Name: monitor_revisions pk_monitor_revisions; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.monitor_revisions
    ADD CONSTRAINT pk_monitor_revisions PRIMARY KEY (id);


--
-- Name: monitors pk_monitors; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.monitors
    ADD CONSTRAINT pk_monitors PRIMARY KEY (id);


--
-- Name: platforms pk_platforms; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.platforms
    ADD CONSTRAINT pk_platforms PRIMARY KEY (id);


--
-- Name: semantic_assignment_methods pk_semantic_assignment_methods; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.semantic_assignment_methods
    ADD CONSTRAINT pk_semantic_assignment_methods PRIMARY KEY (slug);


--
-- Name: semantic_mapping_relations pk_semantic_mapping_relations; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.semantic_mapping_relations
    ADD CONSTRAINT pk_semantic_mapping_relations PRIMARY KEY (slug);


--
-- Name: source_endpoints pk_source_endpoints; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.source_endpoints
    ADD CONSTRAINT pk_source_endpoints PRIMARY KEY (id);


--
-- Name: source_types pk_source_types; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.source_types
    ADD CONSTRAINT pk_source_types PRIMARY KEY (id);


--
-- Name: sources pk_sources; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.sources
    ADD CONSTRAINT pk_sources PRIMARY KEY (id);


--
-- Name: topics pk_topics; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.topics
    ADD CONSTRAINT pk_topics PRIMARY KEY (id);


--
-- Name: acquisition_methods uq_acquisition_methods_slug; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.acquisition_methods
    ADD CONSTRAINT uq_acquisition_methods_slug UNIQUE (slug);


--
-- Name: alert_deliveries uq_alert_deliveries_alert_destination; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.alert_deliveries
    ADD CONSTRAINT uq_alert_deliveries_alert_destination UNIQUE (alert_id, destination_id);


--
-- Name: alert_delivery_attempts uq_alert_delivery_attempts_delivery_claim; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.alert_delivery_attempts
    ADD CONSTRAINT uq_alert_delivery_attempts_delivery_claim UNIQUE (delivery_id, claim_token);


--
-- Name: alert_delivery_attempts uq_alert_delivery_attempts_delivery_number; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.alert_delivery_attempts
    ADD CONSTRAINT uq_alert_delivery_attempts_delivery_number UNIQUE (delivery_id, attempt_number);


--
-- Name: alert_destinations uq_alert_destinations_endpoint; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.alert_destinations
    ADD CONSTRAINT uq_alert_destinations_endpoint UNIQUE (channel, base_url, topic);


--
-- Name: alert_destinations uq_alert_destinations_slug; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.alert_destinations
    ADD CONSTRAINT uq_alert_destinations_slug UNIQUE (slug);


--
-- Name: alerts uq_alerts_monitor_match; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.alerts
    ADD CONSTRAINT uq_alerts_monitor_match UNIQUE (monitor_match_id);


--
-- Name: intelligence_calendar_event_aliases uq_calendar_event_aliases_normalized; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.intelligence_calendar_event_aliases
    ADD CONSTRAINT uq_calendar_event_aliases_normalized UNIQUE (event_id, language_tag, normalized_alias);


--
-- Name: intelligence_calendar_event_documents uq_calendar_event_documents_relationship; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.intelligence_calendar_event_documents
    ADD CONSTRAINT uq_calendar_event_documents_relationship UNIQUE (event_id, document_id, relationship_type);


--
-- Name: intelligence_calendar_event_evidence uq_calendar_event_evidence_fingerprint; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.intelligence_calendar_event_evidence
    ADD CONSTRAINT uq_calendar_event_evidence_fingerprint UNIQUE (event_id, fingerprint);


--
-- Name: intelligence_calendar_event_merge_history uq_calendar_event_merge_history_loser; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.intelligence_calendar_event_merge_history
    ADD CONSTRAINT uq_calendar_event_merge_history_loser UNIQUE (loser_event_id);


--
-- Name: intelligence_calendar_event_monitors uq_calendar_event_monitors_purpose; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.intelligence_calendar_event_monitors
    ADD CONSTRAINT uq_calendar_event_monitors_purpose UNIQUE (event_id, monitor_id, purpose);


--
-- Name: intelligence_calendar_event_revisions uq_calendar_event_revisions_event_id; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.intelligence_calendar_event_revisions
    ADD CONSTRAINT uq_calendar_event_revisions_event_id UNIQUE (event_id, id);


--
-- Name: intelligence_calendar_event_revisions uq_calendar_event_revisions_event_number; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.intelligence_calendar_event_revisions
    ADD CONSTRAINT uq_calendar_event_revisions_event_number UNIQUE (event_id, revision_number);


--
-- Name: intelligence_calendar_events uq_calendar_events_current_revision; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.intelligence_calendar_events
    ADD CONSTRAINT uq_calendar_events_current_revision UNIQUE (id, current_revision_id);


--
-- Name: intelligence_calendar_occurrence_policy_overrides uq_calendar_occurrence_policy_overrides; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.intelligence_calendar_occurrence_policy_overrides
    ADD CONSTRAINT uq_calendar_occurrence_policy_overrides UNIQUE (policy_id, occurrence_id);


--
-- Name: intelligence_calendar_event_occurrences uq_calendar_occurrences_current_schedule; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.intelligence_calendar_event_occurrences
    ADD CONSTRAINT uq_calendar_occurrences_current_schedule UNIQUE (id, current_schedule_revision_id);


--
-- Name: intelligence_calendar_event_occurrences uq_calendar_occurrences_event_id; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.intelligence_calendar_event_occurrences
    ADD CONSTRAINT uq_calendar_occurrences_event_id UNIQUE (event_id, id);


--
-- Name: intelligence_calendar_event_occurrences uq_calendar_occurrences_event_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.intelligence_calendar_event_occurrences
    ADD CONSTRAINT uq_calendar_occurrences_event_key UNIQUE (event_id, recurrence_key);


--
-- Name: intelligence_calendar_event_coverage_policies uq_calendar_policies_event_id; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.intelligence_calendar_event_coverage_policies
    ADD CONSTRAINT uq_calendar_policies_event_id UNIQUE (event_id, id);


--
-- Name: intelligence_calendar_event_coverage_policies uq_calendar_policies_event_profile; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.intelligence_calendar_event_coverage_policies
    ADD CONSTRAINT uq_calendar_policies_event_profile UNIQUE (event_id, profile_id);


--
-- Name: intelligence_calendar_event_coverage_policies uq_calendar_policies_profile_id; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.intelligence_calendar_event_coverage_policies
    ADD CONSTRAINT uq_calendar_policies_profile_id UNIQUE (profile_id, id);


--
-- Name: intelligence_calendar_policy_search_terms uq_calendar_policy_search_terms; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.intelligence_calendar_policy_search_terms
    ADD CONSTRAINT uq_calendar_policy_search_terms UNIQUE (policy_id, language_tag, term_type, term);


--
-- Name: intelligence_calendar_event_recurrence_exceptions uq_calendar_recurrence_exceptions_rule_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.intelligence_calendar_event_recurrence_exceptions
    ADD CONSTRAINT uq_calendar_recurrence_exceptions_rule_key UNIQUE (recurrence_rule_id, recurrence_key);


--
-- Name: intelligence_calendar_event_recurrence_rules uq_calendar_recurrence_rules_event_version; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.intelligence_calendar_event_recurrence_rules
    ADD CONSTRAINT uq_calendar_recurrence_rules_event_version UNIQUE (event_id, version_number);


--
-- Name: intelligence_calendar_occurrence_schedule_revisions uq_calendar_schedule_revisions_occurrence_id; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.intelligence_calendar_occurrence_schedule_revisions
    ADD CONSTRAINT uq_calendar_schedule_revisions_occurrence_id UNIQUE (occurrence_id, id);


--
-- Name: intelligence_calendar_occurrence_schedule_revisions uq_calendar_schedule_revisions_occurrence_number; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.intelligence_calendar_occurrence_schedule_revisions
    ADD CONSTRAINT uq_calendar_schedule_revisions_occurrence_number UNIQUE (occurrence_id, revision_number);


--
-- Name: content_formats uq_content_formats_slug; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.content_formats
    ADD CONSTRAINT uq_content_formats_slug UNIQUE (slug);


--
-- Name: coverage_profile_translation_targets uq_coverage_profile_translation_targets_order; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.coverage_profile_translation_targets
    ADD CONSTRAINT uq_coverage_profile_translation_targets_order UNIQUE (profile_id, preference_order);


--
-- Name: coverage_profiles uq_coverage_profiles_slug; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.coverage_profiles
    ADD CONSTRAINT uq_coverage_profiles_slug UNIQUE (slug);


--
-- Name: document_types uq_document_types_slug; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.document_types
    ADD CONSTRAINT uq_document_types_slug UNIQUE (slug);


--
-- Name: document_versions uq_document_versions_document_hash; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.document_versions
    ADD CONSTRAINT uq_document_versions_document_hash UNIQUE (document_id, content_hash, content_format);


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
-- Name: endpoint_formats uq_endpoint_formats_slug; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.endpoint_formats
    ADD CONSTRAINT uq_endpoint_formats_slug UNIQUE (slug);


--
-- Name: endpoint_types uq_endpoint_types_slug; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.endpoint_types
    ADD CONSTRAINT uq_endpoint_types_slug UNIQUE (slug);


--
-- Name: entity_aliases uq_entity_aliases_entity_normalized_language; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.entity_aliases
    ADD CONSTRAINT uq_entity_aliases_entity_normalized_language UNIQUE (entity_id, normalized_alias, language);


--
-- Name: entity_type_hierarchy_edges uq_entity_type_hierarchy_edges_parent_child; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.entity_type_hierarchy_edges
    ADD CONSTRAINT uq_entity_type_hierarchy_edges_parent_child UNIQUE (parent_entity_type_id, child_entity_type_id);


--
-- Name: entity_types uq_entity_types_slug; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.entity_types
    ADD CONSTRAINT uq_entity_types_slug UNIQUE (slug);


--
-- Name: external_semantic_resources uq_external_semantic_resources_id_kind; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.external_semantic_resources
    ADD CONSTRAINT uq_external_semantic_resources_id_kind UNIQUE (id, resource_kind);


--
-- Name: external_semantic_resources uq_external_semantic_resources_scheme_identifier; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.external_semantic_resources
    ADD CONSTRAINT uq_external_semantic_resources_scheme_identifier UNIQUE (scheme_id, external_identifier);


--
-- Name: external_semantic_schemes uq_external_semantic_schemes_authority_slug; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.external_semantic_schemes
    ADD CONSTRAINT uq_external_semantic_schemes_authority_slug UNIQUE (authority_slug, slug);


--
-- Name: external_semantic_schemes uq_external_semantic_schemes_slug; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.external_semantic_schemes
    ADD CONSTRAINT uq_external_semantic_schemes_slug UNIQUE (slug);


--
-- Name: geographies uq_geographies_slug; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.geographies
    ADD CONSTRAINT uq_geographies_slug UNIQUE (slug);


--
-- Name: intelligence_calendar_event_occurrences uq_intelligence_calendar_event_occurrences_public_id; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.intelligence_calendar_event_occurrences
    ADD CONSTRAINT uq_intelligence_calendar_event_occurrences_public_id UNIQUE (public_id);


--
-- Name: intelligence_calendar_events uq_intelligence_calendar_events_public_id; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.intelligence_calendar_events
    ADD CONSTRAINT uq_intelligence_calendar_events_public_id UNIQUE (public_id);


--
-- Name: monitor_evaluation_runs uq_monitor_evaluation_runs_monitor_id; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.monitor_evaluation_runs
    ADD CONSTRAINT uq_monitor_evaluation_runs_monitor_id UNIQUE (monitor_id, id);


--
-- Name: monitor_matches uq_monitor_matches_monitor_document; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.monitor_matches
    ADD CONSTRAINT uq_monitor_matches_monitor_document UNIQUE (monitor_id, document_id);


--
-- Name: monitor_matches uq_monitor_matches_monitor_id; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.monitor_matches
    ADD CONSTRAINT uq_monitor_matches_monitor_id UNIQUE (monitor_id, id);


--
-- Name: monitor_revisions uq_monitor_revisions_monitor_id; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.monitor_revisions
    ADD CONSTRAINT uq_monitor_revisions_monitor_id UNIQUE (monitor_id, id);


--
-- Name: monitor_revisions uq_monitor_revisions_monitor_number; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.monitor_revisions
    ADD CONSTRAINT uq_monitor_revisions_monitor_number UNIQUE (monitor_id, revision_number);


--
-- Name: monitors uq_monitors_slug; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.monitors
    ADD CONSTRAINT uq_monitors_slug UNIQUE (slug);


--
-- Name: platforms uq_platforms_slug; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.platforms
    ADD CONSTRAINT uq_platforms_slug UNIQUE (slug);


--
-- Name: semantic_mapping_relations uq_semantic_mapping_relations_slug_kind; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.semantic_mapping_relations
    ADD CONSTRAINT uq_semantic_mapping_relations_slug_kind UNIQUE (slug, applicable_resource_kind);


--
-- Name: source_endpoints uq_source_endpoints_url; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.source_endpoints
    ADD CONSTRAINT uq_source_endpoints_url UNIQUE (url);


--
-- Name: source_types uq_source_types_slug; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.source_types
    ADD CONSTRAINT uq_source_types_slug UNIQUE (slug);


--
-- Name: sources uq_sources_website_url; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.sources
    ADD CONSTRAINT uq_sources_website_url UNIQUE (website_url);


--
-- Name: topics uq_topics_slug; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.topics
    ADD CONSTRAINT uq_topics_slug UNIQUE (slug);


--
-- Name: ix_acquisition_methods_active; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_acquisition_methods_active ON public.acquisition_methods USING btree (is_active);


--
-- Name: ix_alert_deliveries_claim_expiry; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_alert_deliveries_claim_expiry ON public.alert_deliveries USING btree (status, claim_expires_at);


--
-- Name: ix_alert_deliveries_destination_status; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_alert_deliveries_destination_status ON public.alert_deliveries USING btree (destination_id, status);


--
-- Name: ix_alert_deliveries_due; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_alert_deliveries_due ON public.alert_deliveries USING btree (status, next_attempt_at);


--
-- Name: ix_alert_delivery_attempts_delivery_started; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_alert_delivery_attempts_delivery_started ON public.alert_delivery_attempts USING btree (delivery_id, started_at);


--
-- Name: ix_alert_destinations_active_name; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_alert_destinations_active_name ON public.alert_destinations USING btree (is_active, name);


--
-- Name: ix_alerts_created; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_alerts_created ON public.alerts USING btree (created_at);


--
-- Name: ix_alerts_monitor_created; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_alerts_monitor_created ON public.alerts USING btree (monitor_id, created_at);


--
-- Name: ix_calendar_events_state_created; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_calendar_events_state_created ON public.intelligence_calendar_events USING btree (identity_state, created_at);


--
-- Name: ix_calendar_occurrences_event_state; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_calendar_occurrences_event_state ON public.intelligence_calendar_event_occurrences USING btree (event_id, schedule_state);


--
-- Name: ix_calendar_schedule_revisions_date_start; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_calendar_schedule_revisions_date_start ON public.intelligence_calendar_occurrence_schedule_revisions USING btree (start_date);


--
-- Name: ix_calendar_schedule_revisions_timed_start; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_calendar_schedule_revisions_timed_start ON public.intelligence_calendar_occurrence_schedule_revisions USING btree (scheduled_start_at);


--
-- Name: ix_classification_runs_document_started; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_classification_runs_document_started ON public.classification_runs USING btree (document_id, started_at);


--
-- Name: ix_classification_runs_status_started; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_classification_runs_status_started ON public.classification_runs USING btree (status, started_at);


--
-- Name: ix_content_formats_active; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_content_formats_active ON public.content_formats USING btree (is_active);


--
-- Name: ix_coverage_profile_content_formats_content_format; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_coverage_profile_content_formats_content_format ON public.coverage_profile_content_formats USING btree (content_format_slug);


--
-- Name: ix_coverage_profile_document_types_document_type; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_coverage_profile_document_types_document_type ON public.coverage_profile_document_types USING btree (document_type_id);


--
-- Name: ix_coverage_profile_geographies_geography; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_coverage_profile_geographies_geography ON public.coverage_profile_geographies USING btree (geography_id);


--
-- Name: ix_coverage_profile_languages_language; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_coverage_profile_languages_language ON public.coverage_profile_languages USING btree (language_tag);


--
-- Name: ix_coverage_profile_source_polling_overrides_source; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_coverage_profile_source_polling_overrides_source ON public.coverage_profile_source_polling_overrides USING btree (source_id);


--
-- Name: ix_coverage_profile_source_types_source_type; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_coverage_profile_source_types_source_type ON public.coverage_profile_source_types USING btree (source_type_slug);


--
-- Name: ix_coverage_profile_sources_source; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_coverage_profile_sources_source ON public.coverage_profile_sources USING btree (source_id);


--
-- Name: ix_coverage_profile_topics_topic; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_coverage_profile_topics_topic ON public.coverage_profile_topics USING btree (topic_id);


--
-- Name: ix_coverage_profile_translation_targets_language; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_coverage_profile_translation_targets_language ON public.coverage_profile_translation_targets USING btree (language_tag);


--
-- Name: ix_coverage_profiles_active_name; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_coverage_profiles_active_name ON public.coverage_profiles USING btree (is_active, name);


--
-- Name: ix_document_entities_classification_run; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_document_entities_classification_run ON public.document_entities USING btree (classification_run_id);


--
-- Name: ix_document_entities_document_active; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_document_entities_document_active ON public.document_entities USING btree (document_id, is_active);


--
-- Name: ix_document_entities_entity_active; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_document_entities_entity_active ON public.document_entities USING btree (entity_id, is_active);


--
-- Name: ix_document_geographies_classification_run; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_document_geographies_classification_run ON public.document_geographies USING btree (classification_run_id);


--
-- Name: ix_document_geographies_document_active; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_document_geographies_document_active ON public.document_geographies USING btree (document_id, is_active);


--
-- Name: ix_document_geographies_geography_active; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_document_geographies_geography_active ON public.document_geographies USING btree (geography_id, is_active);


--
-- Name: ix_document_topics_classification_run; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_document_topics_classification_run ON public.document_topics USING btree (classification_run_id);


--
-- Name: ix_document_topics_document_active; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_document_topics_document_active ON public.document_topics USING btree (document_id, is_active);


--
-- Name: ix_document_topics_topic_active; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_document_topics_topic_active ON public.document_topics USING btree (topic_id, is_active);


--
-- Name: ix_document_type_assignments_classification_run; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_document_type_assignments_classification_run ON public.document_type_assignments USING btree (classification_run_id);


--
-- Name: ix_document_type_assignments_document_active; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_document_type_assignments_document_active ON public.document_type_assignments USING btree (document_id, is_active);


--
-- Name: ix_document_type_assignments_document_type_active; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_document_type_assignments_document_type_active ON public.document_type_assignments USING btree (document_type_id, is_active);


--
-- Name: ix_document_types_active_name; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_document_types_active_name ON public.document_types USING btree (is_active, name);


--
-- Name: ix_document_types_parent_name; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_document_types_parent_name ON public.document_types USING btree (parent_id, name);


--
-- Name: ix_document_versions_content_format; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_document_versions_content_format ON public.document_versions USING btree (content_format);


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
-- Name: ix_documents_content_format_published_at; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_documents_content_format_published_at ON public.documents USING btree (content_format, published_at);


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
-- Name: ix_documents_ingestion_format_published_at; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_documents_ingestion_format_published_at ON public.documents USING btree (ingestion_format, published_at);


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
-- Name: ix_endpoint_formats_active; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_endpoint_formats_active ON public.endpoint_formats USING btree (is_active);


--
-- Name: ix_endpoint_types_active; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_endpoint_types_active ON public.endpoint_types USING btree (is_active);


--
-- Name: ix_entities_canonical_name; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_entities_canonical_name ON public.entities USING btree (canonical_name);


--
-- Name: ix_entity_aliases_normalized_language; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_entity_aliases_normalized_language ON public.entity_aliases USING btree (normalized_alias, language);


--
-- Name: ix_entity_geographies_entity_active; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_entity_geographies_entity_active ON public.entity_geographies USING btree (entity_id, is_active);


--
-- Name: ix_entity_geographies_geography_active; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_entity_geographies_geography_active ON public.entity_geographies USING btree (geography_id, is_active);


--
-- Name: ix_entity_geographies_relationship_active; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_entity_geographies_relationship_active ON public.entity_geographies USING btree (relationship_type, is_active);


--
-- Name: ix_entity_geographies_validity; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_entity_geographies_validity ON public.entity_geographies USING btree (valid_from, valid_to);


--
-- Name: ix_entity_type_assignments_entity_active; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_entity_type_assignments_entity_active ON public.entity_type_assignments USING btree (entity_id, is_active);


--
-- Name: ix_entity_type_assignments_type_active; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_entity_type_assignments_type_active ON public.entity_type_assignments USING btree (entity_type_id, is_active);


--
-- Name: ix_entity_type_hierarchy_edges_child; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_entity_type_hierarchy_edges_child ON public.entity_type_hierarchy_edges USING btree (child_entity_type_id);


--
-- Name: ix_entity_types_active_name; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_entity_types_active_name ON public.entity_types USING btree (is_active, name);


--
-- Name: ix_external_semantic_resources_kind_active; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_external_semantic_resources_kind_active ON public.external_semantic_resources USING btree (resource_kind, is_active);


--
-- Name: ix_external_semantic_schemes_active; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_external_semantic_schemes_active ON public.external_semantic_schemes USING btree (is_active);


--
-- Name: ix_geographies_parent_name; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_geographies_parent_name ON public.geographies USING btree (parent_id, name);


--
-- Name: ix_geographies_type_active; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_geographies_type_active ON public.geographies USING btree (geography_type, is_active);


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
-- Name: ix_language_tag_aliases_canonical_active; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_language_tag_aliases_canonical_active ON public.language_tag_aliases USING btree (canonical_tag, is_active);


--
-- Name: ix_language_tags_active; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_language_tags_active ON public.language_tags USING btree (is_active);


--
-- Name: ix_language_tags_language_script_region; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_language_tags_language_script_region ON public.language_tags USING btree (language_subtag, script_subtag, region_subtag);


--
-- Name: ix_language_tags_language_subtag; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_language_tags_language_subtag ON public.language_tags USING btree (language_subtag);


--
-- Name: ix_language_tags_region_subtag; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_language_tags_region_subtag ON public.language_tags USING btree (region_subtag);


--
-- Name: ix_language_tags_script_subtag; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_language_tags_script_subtag ON public.language_tags USING btree (script_subtag);


--
-- Name: ix_monitor_evaluation_runs_monitor_started; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_monitor_evaluation_runs_monitor_started ON public.monitor_evaluation_runs USING btree (monitor_id, started_at);


--
-- Name: ix_monitor_evaluation_runs_status_started; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_monitor_evaluation_runs_status_started ON public.monitor_evaluation_runs USING btree (status, started_at);


--
-- Name: ix_monitor_matches_document; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_monitor_matches_document ON public.monitor_matches USING btree (document_id);


--
-- Name: ix_monitor_matches_monitor_last; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_monitor_matches_monitor_last ON public.monitor_matches USING btree (monitor_id, last_matched_at);


--
-- Name: ix_monitor_revisions_monitor_created; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_monitor_revisions_monitor_created ON public.monitor_revisions USING btree (monitor_id, created_at);


--
-- Name: ix_monitors_profile_status; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_monitors_profile_status ON public.monitors USING btree (coverage_profile_id, status);


--
-- Name: ix_monitors_status_expires; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_monitors_status_expires ON public.monitors USING btree (status, expires_at);


--
-- Name: ix_platforms_active; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_platforms_active ON public.platforms USING btree (is_active);


--
-- Name: ix_source_endpoints_acquisition_method; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_source_endpoints_acquisition_method ON public.source_endpoints USING btree (acquisition_method);


--
-- Name: ix_source_endpoints_due_poll; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_source_endpoints_due_poll ON public.source_endpoints USING btree (status, next_poll_at);


--
-- Name: ix_source_endpoints_endpoint_format; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_source_endpoints_endpoint_format ON public.source_endpoints USING btree (endpoint_format);


--
-- Name: ix_source_endpoints_endpoint_type; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_source_endpoints_endpoint_type ON public.source_endpoints USING btree (endpoint_type);


--
-- Name: ix_source_endpoints_platform; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_source_endpoints_platform ON public.source_endpoints USING btree (platform);


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
-- Name: ix_source_types_active; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_source_types_active ON public.source_types USING btree (is_active);


--
-- Name: ix_source_types_parent_name; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_source_types_parent_name ON public.source_types USING btree (parent_id, name);


--
-- Name: ix_sources_country; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_sources_country ON public.sources USING btree (country);


--
-- Name: ix_sources_country_status; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_sources_country_status ON public.sources USING btree (country, status);


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
-- Name: ix_topics_active_sort_order; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_topics_active_sort_order ON public.topics USING btree (is_active, sort_order);


--
-- Name: ix_topics_parent_sort_order; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_topics_parent_sort_order ON public.topics USING btree (parent_id, sort_order);


--
-- Name: uq_calendar_event_entities_active; Type: INDEX; Schema: public; Owner: -
--

CREATE UNIQUE INDEX uq_calendar_event_entities_active ON public.intelligence_calendar_event_entities USING btree (event_id, entity_id, role) WHERE (retracted_at IS NULL);


--
-- Name: uq_calendar_event_geographies_active; Type: INDEX; Schema: public; Owner: -
--

CREATE UNIQUE INDEX uq_calendar_event_geographies_active ON public.intelligence_calendar_event_geographies USING btree (event_id, geography_id, role) WHERE (retracted_at IS NULL);


--
-- Name: uq_calendar_event_sources_active; Type: INDEX; Schema: public; Owner: -
--

CREATE UNIQUE INDEX uq_calendar_event_sources_active ON public.intelligence_calendar_event_sources USING btree (event_id, source_id, role) WHERE (retracted_at IS NULL);


--
-- Name: uq_calendar_event_topics_active; Type: INDEX; Schema: public; Owner: -
--

CREATE UNIQUE INDEX uq_calendar_event_topics_active ON public.intelligence_calendar_event_topics USING btree (event_id, topic_id, role) WHERE (retracted_at IS NULL);


--
-- Name: uq_calendar_policy_watch_sources_endpoint; Type: INDEX; Schema: public; Owner: -
--

CREATE UNIQUE INDEX uq_calendar_policy_watch_sources_endpoint ON public.intelligence_calendar_policy_watch_sources USING btree (policy_id, source_endpoint_id) WHERE (source_endpoint_id IS NOT NULL);


--
-- Name: uq_calendar_policy_watch_sources_source; Type: INDEX; Schema: public; Owner: -
--

CREATE UNIQUE INDEX uq_calendar_policy_watch_sources_source ON public.intelligence_calendar_policy_watch_sources USING btree (policy_id, source_id) WHERE (source_endpoint_id IS NULL);


--
-- Name: uq_calendar_recurrence_rules_active; Type: INDEX; Schema: public; Owner: -
--

CREATE UNIQUE INDEX uq_calendar_recurrence_rules_active ON public.intelligence_calendar_event_recurrence_rules USING btree (event_id) WHERE ((status)::text = 'active'::text);


--
-- Name: uq_coverage_profiles_default; Type: INDEX; Schema: public; Owner: -
--

CREATE UNIQUE INDEX uq_coverage_profiles_default ON public.coverage_profiles USING btree (is_default) WHERE is_default;


--
-- Name: uq_document_entities_active_relationship; Type: INDEX; Schema: public; Owner: -
--

CREATE UNIQUE INDEX uq_document_entities_active_relationship ON public.document_entities USING btree (document_id, entity_id, entity_role) WHERE is_active;


--
-- Name: uq_document_geographies_active_relationship; Type: INDEX; Schema: public; Owner: -
--

CREATE UNIQUE INDEX uq_document_geographies_active_relationship ON public.document_geographies USING btree (document_id, geography_id, relationship_role) WHERE is_active;


--
-- Name: uq_document_topics_active_relationship; Type: INDEX; Schema: public; Owner: -
--

CREATE UNIQUE INDEX uq_document_topics_active_relationship ON public.document_topics USING btree (document_id, topic_id, relationship_role) WHERE is_active;


--
-- Name: uq_document_type_assignments_active_primary; Type: INDEX; Schema: public; Owner: -
--

CREATE UNIQUE INDEX uq_document_type_assignments_active_primary ON public.document_type_assignments USING btree (document_id) WHERE (is_active AND is_primary);


--
-- Name: uq_document_type_assignments_active_type; Type: INDEX; Schema: public; Owner: -
--

CREATE UNIQUE INDEX uq_document_type_assignments_active_type ON public.document_type_assignments USING btree (document_id, document_type_id) WHERE is_active;


--
-- Name: uq_entity_geographies_active_fact; Type: INDEX; Schema: public; Owner: -
--

CREATE UNIQUE INDEX uq_entity_geographies_active_fact ON public.entity_geographies USING btree (entity_id, geography_id, relationship_type) WHERE is_active;


--
-- Name: uq_entity_geography_type_external_mappings_active; Type: INDEX; Schema: public; Owner: -
--

CREATE UNIQUE INDEX uq_entity_geography_type_external_mappings_active ON public.entity_geography_relationship_type_external_mappings USING btree (relationship_type, external_resource_id) WHERE is_active;


--
-- Name: uq_entity_type_assignments_active_primary; Type: INDEX; Schema: public; Owner: -
--

CREATE UNIQUE INDEX uq_entity_type_assignments_active_primary ON public.entity_type_assignments USING btree (entity_id) WHERE (is_active AND is_primary);


--
-- Name: uq_entity_type_assignments_active_type; Type: INDEX; Schema: public; Owner: -
--

CREATE UNIQUE INDEX uq_entity_type_assignments_active_type ON public.entity_type_assignments USING btree (entity_id, entity_type_id) WHERE is_active;


--
-- Name: uq_entity_type_external_mappings_active; Type: INDEX; Schema: public; Owner: -
--

CREATE UNIQUE INDEX uq_entity_type_external_mappings_active ON public.entity_type_external_mappings USING btree (entity_type_id, external_resource_id) WHERE is_active;


--
-- Name: uq_external_semantic_resources_active_uri; Type: INDEX; Schema: public; Owner: -
--

CREATE UNIQUE INDEX uq_external_semantic_resources_active_uri ON public.external_semantic_resources USING btree (external_uri) WHERE (is_active AND (external_uri IS NOT NULL));


--
-- Name: uq_geographies_iso_alpha2; Type: INDEX; Schema: public; Owner: -
--

CREATE UNIQUE INDEX uq_geographies_iso_alpha2 ON public.geographies USING btree (iso_alpha2) WHERE (iso_alpha2 IS NOT NULL);


--
-- Name: uq_geographies_iso_alpha3; Type: INDEX; Schema: public; Owner: -
--

CREATE UNIQUE INDEX uq_geographies_iso_alpha3 ON public.geographies USING btree (iso_alpha3) WHERE (iso_alpha3 IS NOT NULL);


--
-- Name: alert_delivery_attempts alert_delivery_attempts_preserve_history; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER alert_delivery_attempts_preserve_history BEFORE DELETE OR UPDATE ON public.alert_delivery_attempts FOR EACH ROW EXECUTE FUNCTION public.preserve_completed_alert_attempt();


--
-- Name: alerts alerts_preserve_immutability; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER alerts_preserve_immutability BEFORE DELETE OR UPDATE ON public.alerts FOR EACH ROW EXECUTE FUNCTION public.preserve_alert_event();


--
-- Name: alerts alerts_require_match_provenance; Type: TRIGGER; Schema: public; Owner: -
--

CREATE CONSTRAINT TRIGGER alerts_require_match_provenance AFTER INSERT OR UPDATE OF monitor_id, monitor_match_id, monitor_revision_id, document_id ON public.alerts DEFERRABLE INITIALLY DEFERRED FOR EACH ROW EXECUTE FUNCTION public.require_alert_match_provenance();


--
-- Name: entity_type_hierarchy_edges ck_entity_type_hierarchy_edges_acyclic; Type: TRIGGER; Schema: public; Owner: -
--

CREATE CONSTRAINT TRIGGER ck_entity_type_hierarchy_edges_acyclic AFTER INSERT OR UPDATE OF parent_entity_type_id, child_entity_type_id ON public.entity_type_hierarchy_edges DEFERRABLE INITIALLY IMMEDIATE FOR EACH ROW EXECUTE FUNCTION public.prevent_entity_type_hierarchy_cycle();


--
-- Name: coverage_profiles coverage_profiles_require_default; Type: TRIGGER; Schema: public; Owner: -
--

CREATE CONSTRAINT TRIGGER coverage_profiles_require_default AFTER INSERT OR DELETE OR UPDATE ON public.coverage_profiles DEFERRABLE INITIALLY DEFERRED FOR EACH ROW EXECUTE FUNCTION public.require_default_coverage_profile();


--
-- Name: monitor_matches matches_preserve_alert_provenance; Type: TRIGGER; Schema: public; Owner: -
--

CREATE CONSTRAINT TRIGGER matches_preserve_alert_provenance AFTER UPDATE OF monitor_id, document_id, first_monitor_revision_id ON public.monitor_matches DEFERRABLE INITIALLY DEFERRED FOR EACH ROW EXECUTE FUNCTION public.require_alert_match_provenance();


--
-- Name: monitor_revision_content_formats monitor_revision_content_formats_preserve_immutability; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER monitor_revision_content_formats_preserve_immutability BEFORE INSERT OR DELETE OR UPDATE ON public.monitor_revision_content_formats FOR EACH ROW EXECUTE FUNCTION public.preserve_monitor_revision_selectors();


--
-- Name: monitor_revision_document_types monitor_revision_document_types_preserve_immutability; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER monitor_revision_document_types_preserve_immutability BEFORE INSERT OR DELETE OR UPDATE ON public.monitor_revision_document_types FOR EACH ROW EXECUTE FUNCTION public.preserve_monitor_revision_selectors();


--
-- Name: monitor_revision_entities monitor_revision_entities_preserve_immutability; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER monitor_revision_entities_preserve_immutability BEFORE INSERT OR DELETE OR UPDATE ON public.monitor_revision_entities FOR EACH ROW EXECUTE FUNCTION public.preserve_monitor_revision_selectors();


--
-- Name: monitor_revision_entity_roles monitor_revision_entity_roles_preserve_immutability; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER monitor_revision_entity_roles_preserve_immutability BEFORE INSERT OR DELETE OR UPDATE ON public.monitor_revision_entity_roles FOR EACH ROW EXECUTE FUNCTION public.preserve_monitor_revision_selectors();


--
-- Name: monitor_revision_geographies monitor_revision_geographies_preserve_immutability; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER monitor_revision_geographies_preserve_immutability BEFORE INSERT OR DELETE OR UPDATE ON public.monitor_revision_geographies FOR EACH ROW EXECUTE FUNCTION public.preserve_monitor_revision_selectors();


--
-- Name: monitor_revision_languages monitor_revision_languages_preserve_immutability; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER monitor_revision_languages_preserve_immutability BEFORE INSERT OR DELETE OR UPDATE ON public.monitor_revision_languages FOR EACH ROW EXECUTE FUNCTION public.preserve_monitor_revision_selectors();


--
-- Name: monitor_revision_source_types monitor_revision_source_types_preserve_immutability; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER monitor_revision_source_types_preserve_immutability BEFORE INSERT OR DELETE OR UPDATE ON public.monitor_revision_source_types FOR EACH ROW EXECUTE FUNCTION public.preserve_monitor_revision_selectors();


--
-- Name: monitor_revision_sources monitor_revision_sources_preserve_immutability; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER monitor_revision_sources_preserve_immutability BEFORE INSERT OR DELETE OR UPDATE ON public.monitor_revision_sources FOR EACH ROW EXECUTE FUNCTION public.preserve_monitor_revision_selectors();


--
-- Name: monitor_revision_topics monitor_revision_topics_preserve_immutability; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER monitor_revision_topics_preserve_immutability BEFORE INSERT OR DELETE OR UPDATE ON public.monitor_revision_topics FOR EACH ROW EXECUTE FUNCTION public.preserve_monitor_revision_selectors();


--
-- Name: monitor_revisions monitor_revisions_preserve_immutability; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER monitor_revisions_preserve_immutability BEFORE DELETE OR UPDATE ON public.monitor_revisions FOR EACH ROW EXECUTE FUNCTION public.preserve_monitor_revision_immutability();


--
-- Name: monitor_revisions monitor_revisions_require_seal; Type: TRIGGER; Schema: public; Owner: -
--

CREATE CONSTRAINT TRIGGER monitor_revisions_require_seal AFTER INSERT OR UPDATE OF sealed_at ON public.monitor_revisions DEFERRABLE INITIALLY DEFERRED FOR EACH ROW EXECUTE FUNCTION public.require_monitor_revisions_sealed();


--
-- Name: monitors monitors_require_current_revision; Type: TRIGGER; Schema: public; Owner: -
--

CREATE CONSTRAINT TRIGGER monitors_require_current_revision AFTER INSERT OR UPDATE OF id, current_revision_number ON public.monitors DEFERRABLE INITIALLY DEFERRED FOR EACH ROW EXECUTE FUNCTION public.require_monitor_current_revision();


--
-- Name: monitor_revisions revisions_preserve_monitor_current; Type: TRIGGER; Schema: public; Owner: -
--

CREATE CONSTRAINT TRIGGER revisions_preserve_monitor_current AFTER DELETE OR UPDATE OF monitor_id, revision_number ON public.monitor_revisions DEFERRABLE INITIALLY DEFERRED FOR EACH ROW EXECUTE FUNCTION public.require_monitor_current_revision();


--
-- Name: intelligence_calendar_event_evidence trg_calendar_evidence_source; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER trg_calendar_evidence_source BEFORE INSERT ON public.intelligence_calendar_event_evidence FOR EACH ROW EXECUTE FUNCTION public.calendar_validate_evidence_source();


--
-- Name: intelligence_calendar_event_merge_history trg_calendar_merge_history; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER trg_calendar_merge_history BEFORE INSERT ON public.intelligence_calendar_event_merge_history FOR EACH ROW EXECUTE FUNCTION public.calendar_validate_merge();


--
-- Name: intelligence_calendar_event_monitors trg_calendar_monitor_profile; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER trg_calendar_monitor_profile BEFORE INSERT OR UPDATE ON public.intelligence_calendar_event_monitors FOR EACH ROW EXECUTE FUNCTION public.calendar_validate_monitor_profile();


--
-- Name: intelligence_calendar_occurrence_policy_overrides trg_calendar_policy_override_event; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER trg_calendar_policy_override_event BEFORE INSERT OR UPDATE ON public.intelligence_calendar_occurrence_policy_overrides FOR EACH ROW EXECUTE FUNCTION public.calendar_validate_policy_override();


--
-- Name: intelligence_calendar_event_recurrence_rules trg_calendar_recurrence_rules_sealed; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER trg_calendar_recurrence_rules_sealed BEFORE UPDATE ON public.intelligence_calendar_event_recurrence_rules FOR EACH ROW EXECUTE FUNCTION public.calendar_restrict_recurrence_rule_mutation();


--
-- Name: intelligence_calendar_policy_watch_sources trg_calendar_watch_endpoint_source; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER trg_calendar_watch_endpoint_source BEFORE INSERT OR UPDATE ON public.intelligence_calendar_policy_watch_sources FOR EACH ROW EXECUTE FUNCTION public.calendar_validate_watch_endpoint();


--
-- Name: intelligence_calendar_event_entities trg_intelligence_calendar_event_entities_retraction_only; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER trg_intelligence_calendar_event_entities_retraction_only BEFORE DELETE OR UPDATE ON public.intelligence_calendar_event_entities FOR EACH ROW EXECUTE FUNCTION public.calendar_restrict_assertion_mutation();


--
-- Name: intelligence_calendar_event_evidence trg_intelligence_calendar_event_evidence_append_only; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER trg_intelligence_calendar_event_evidence_append_only BEFORE DELETE OR UPDATE ON public.intelligence_calendar_event_evidence FOR EACH ROW EXECUTE FUNCTION public.calendar_reject_mutation();


--
-- Name: intelligence_calendar_event_geographies trg_intelligence_calendar_event_geographies_retraction_only; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER trg_intelligence_calendar_event_geographies_retraction_only BEFORE DELETE OR UPDATE ON public.intelligence_calendar_event_geographies FOR EACH ROW EXECUTE FUNCTION public.calendar_restrict_assertion_mutation();


--
-- Name: intelligence_calendar_event_merge_history trg_intelligence_calendar_event_merge_history_append_only; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER trg_intelligence_calendar_event_merge_history_append_only BEFORE DELETE OR UPDATE ON public.intelligence_calendar_event_merge_history FOR EACH ROW EXECUTE FUNCTION public.calendar_reject_mutation();


--
-- Name: intelligence_calendar_event_occurrences trg_intelligence_calendar_event_occurrences_shape; Type: TRIGGER; Schema: public; Owner: -
--

CREATE CONSTRAINT TRIGGER trg_intelligence_calendar_event_occurrences_shape AFTER INSERT OR DELETE OR UPDATE ON public.intelligence_calendar_event_occurrences DEFERRABLE INITIALLY DEFERRED FOR EACH ROW EXECUTE FUNCTION public.calendar_validate_event_shape();


--
-- Name: intelligence_calendar_event_recurrence_rules trg_intelligence_calendar_event_recurrence_rules_shape; Type: TRIGGER; Schema: public; Owner: -
--

CREATE CONSTRAINT TRIGGER trg_intelligence_calendar_event_recurrence_rules_shape AFTER INSERT OR DELETE OR UPDATE ON public.intelligence_calendar_event_recurrence_rules DEFERRABLE INITIALLY DEFERRED FOR EACH ROW EXECUTE FUNCTION public.calendar_validate_event_shape();


--
-- Name: intelligence_calendar_event_recurrence_rules trg_intelligence_calendar_event_recurrence_rules_timezone; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER trg_intelligence_calendar_event_recurrence_rules_timezone BEFORE INSERT OR UPDATE ON public.intelligence_calendar_event_recurrence_rules FOR EACH ROW EXECUTE FUNCTION public.calendar_validate_timezone();


--
-- Name: intelligence_calendar_event_revisions trg_intelligence_calendar_event_revisions_append_only; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER trg_intelligence_calendar_event_revisions_append_only BEFORE DELETE OR UPDATE ON public.intelligence_calendar_event_revisions FOR EACH ROW EXECUTE FUNCTION public.calendar_reject_mutation();


--
-- Name: intelligence_calendar_event_sources trg_intelligence_calendar_event_sources_retraction_only; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER trg_intelligence_calendar_event_sources_retraction_only BEFORE DELETE OR UPDATE ON public.intelligence_calendar_event_sources FOR EACH ROW EXECUTE FUNCTION public.calendar_restrict_assertion_mutation();


--
-- Name: intelligence_calendar_event_state_transitions trg_intelligence_calendar_event_state_transitions_append_only; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER trg_intelligence_calendar_event_state_transitions_append_only BEFORE DELETE OR UPDATE ON public.intelligence_calendar_event_state_transitions FOR EACH ROW EXECUTE FUNCTION public.calendar_reject_mutation();


--
-- Name: intelligence_calendar_event_topics trg_intelligence_calendar_event_topics_retraction_only; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER trg_intelligence_calendar_event_topics_retraction_only BEFORE DELETE OR UPDATE ON public.intelligence_calendar_event_topics FOR EACH ROW EXECUTE FUNCTION public.calendar_restrict_assertion_mutation();


--
-- Name: intelligence_calendar_events trg_intelligence_calendar_events_shape; Type: TRIGGER; Schema: public; Owner: -
--

CREATE CONSTRAINT TRIGGER trg_intelligence_calendar_events_shape AFTER INSERT OR DELETE OR UPDATE ON public.intelligence_calendar_events DEFERRABLE INITIALLY DEFERRED FOR EACH ROW EXECUTE FUNCTION public.calendar_validate_event_shape();


--
-- Name: intelligence_calendar_occurrence_schedule_revisions trg_intelligence_calendar_occurrence_schedule_revisions_append_; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER trg_intelligence_calendar_occurrence_schedule_revisions_append_ BEFORE DELETE OR UPDATE ON public.intelligence_calendar_occurrence_schedule_revisions FOR EACH ROW EXECUTE FUNCTION public.calendar_reject_mutation();


--
-- Name: intelligence_calendar_occurrence_schedule_revisions trg_intelligence_calendar_occurrence_schedule_revisions_timezon; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER trg_intelligence_calendar_occurrence_schedule_revisions_timezon BEFORE INSERT OR UPDATE ON public.intelligence_calendar_occurrence_schedule_revisions FOR EACH ROW EXECUTE FUNCTION public.calendar_validate_timezone();


--
-- Name: alert_deliveries fk_alert_deliveries_alert_id_alerts; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.alert_deliveries
    ADD CONSTRAINT fk_alert_deliveries_alert_id_alerts FOREIGN KEY (alert_id) REFERENCES public.alerts(id) ON DELETE RESTRICT;


--
-- Name: alert_deliveries fk_alert_deliveries_destination_id_alert_destinations; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.alert_deliveries
    ADD CONSTRAINT fk_alert_deliveries_destination_id_alert_destinations FOREIGN KEY (destination_id) REFERENCES public.alert_destinations(id) ON DELETE RESTRICT;


--
-- Name: alert_delivery_attempts fk_alert_delivery_attempts_delivery_id_alert_deliveries; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.alert_delivery_attempts
    ADD CONSTRAINT fk_alert_delivery_attempts_delivery_id_alert_deliveries FOREIGN KEY (delivery_id) REFERENCES public.alert_deliveries(id) ON DELETE RESTRICT;


--
-- Name: alerts fk_alerts_document_id_documents; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.alerts
    ADD CONSTRAINT fk_alerts_document_id_documents FOREIGN KEY (document_id) REFERENCES public.documents(id) ON DELETE RESTRICT;


--
-- Name: alerts fk_alerts_monitor_match; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.alerts
    ADD CONSTRAINT fk_alerts_monitor_match FOREIGN KEY (monitor_id, monitor_match_id) REFERENCES public.monitor_matches(monitor_id, id) ON DELETE RESTRICT;


--
-- Name: alerts fk_alerts_monitor_revision; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.alerts
    ADD CONSTRAINT fk_alerts_monitor_revision FOREIGN KEY (monitor_id, monitor_revision_id) REFERENCES public.monitor_revisions(monitor_id, id) ON DELETE RESTRICT;


--
-- Name: intelligence_calendar_event_documents fk_calendar_event_documents_occurrence; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.intelligence_calendar_event_documents
    ADD CONSTRAINT fk_calendar_event_documents_occurrence FOREIGN KEY (event_id, occurrence_id) REFERENCES public.intelligence_calendar_event_occurrences(event_id, id) ON DELETE CASCADE;


--
-- Name: intelligence_calendar_event_monitors fk_calendar_event_monitors_occurrence; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.intelligence_calendar_event_monitors
    ADD CONSTRAINT fk_calendar_event_monitors_occurrence FOREIGN KEY (event_id, occurrence_id) REFERENCES public.intelligence_calendar_event_occurrences(event_id, id) ON DELETE CASCADE;


--
-- Name: intelligence_calendar_event_monitors fk_calendar_event_monitors_policy; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.intelligence_calendar_event_monitors
    ADD CONSTRAINT fk_calendar_event_monitors_policy FOREIGN KEY (event_id, policy_id) REFERENCES public.intelligence_calendar_event_coverage_policies(event_id, id) ON DELETE CASCADE;


--
-- Name: intelligence_calendar_events fk_calendar_events_current_revision; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.intelligence_calendar_events
    ADD CONSTRAINT fk_calendar_events_current_revision FOREIGN KEY (id, current_revision_id) REFERENCES public.intelligence_calendar_event_revisions(event_id, id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: intelligence_calendar_event_evidence fk_calendar_evidence_occurrence; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.intelligence_calendar_event_evidence
    ADD CONSTRAINT fk_calendar_evidence_occurrence FOREIGN KEY (event_id, occurrence_id) REFERENCES public.intelligence_calendar_event_occurrences(event_id, id) ON DELETE CASCADE;


--
-- Name: intelligence_calendar_event_occurrences fk_calendar_occurrences_current_schedule; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.intelligence_calendar_event_occurrences
    ADD CONSTRAINT fk_calendar_occurrences_current_schedule FOREIGN KEY (id, current_schedule_revision_id) REFERENCES public.intelligence_calendar_occurrence_schedule_revisions(occurrence_id, id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: intelligence_calendar_event_state_transitions fk_calendar_transitions_occurrence; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.intelligence_calendar_event_state_transitions
    ADD CONSTRAINT fk_calendar_transitions_occurrence FOREIGN KEY (event_id, occurrence_id) REFERENCES public.intelligence_calendar_event_occurrences(event_id, id) ON DELETE CASCADE;


--
-- Name: classification_runs fk_classification_runs_document_id_documents; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.classification_runs
    ADD CONSTRAINT fk_classification_runs_document_id_documents FOREIGN KEY (document_id) REFERENCES public.documents(id) ON DELETE CASCADE;


--
-- Name: classification_runs fk_classification_runs_language_language_tags_tag; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.classification_runs
    ADD CONSTRAINT fk_classification_runs_language_language_tags_tag FOREIGN KEY (language) REFERENCES public.language_tags(tag) ON DELETE RESTRICT;


--
-- Name: coverage_profile_content_formats fk_coverage_profile_content_formats_content_format_slug_815f; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.coverage_profile_content_formats
    ADD CONSTRAINT fk_coverage_profile_content_formats_content_format_slug_815f FOREIGN KEY (content_format_slug) REFERENCES public.content_formats(slug) ON DELETE RESTRICT;


--
-- Name: coverage_profile_content_formats fk_coverage_profile_content_formats_profile_id_coverage_ddbc; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.coverage_profile_content_formats
    ADD CONSTRAINT fk_coverage_profile_content_formats_profile_id_coverage_ddbc FOREIGN KEY (profile_id) REFERENCES public.coverage_profiles(id) ON DELETE CASCADE;


--
-- Name: coverage_profile_document_types fk_coverage_profile_document_types_document_type_id_doc_5404; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.coverage_profile_document_types
    ADD CONSTRAINT fk_coverage_profile_document_types_document_type_id_doc_5404 FOREIGN KEY (document_type_id) REFERENCES public.document_types(id) ON DELETE RESTRICT;


--
-- Name: coverage_profile_document_types fk_coverage_profile_document_types_profile_id_coverage_profiles; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.coverage_profile_document_types
    ADD CONSTRAINT fk_coverage_profile_document_types_profile_id_coverage_profiles FOREIGN KEY (profile_id) REFERENCES public.coverage_profiles(id) ON DELETE CASCADE;


--
-- Name: coverage_profile_geographies fk_coverage_profile_geographies_geography_id_geographies; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.coverage_profile_geographies
    ADD CONSTRAINT fk_coverage_profile_geographies_geography_id_geographies FOREIGN KEY (geography_id) REFERENCES public.geographies(id) ON DELETE RESTRICT;


--
-- Name: coverage_profile_geographies fk_coverage_profile_geographies_profile_id_coverage_profiles; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.coverage_profile_geographies
    ADD CONSTRAINT fk_coverage_profile_geographies_profile_id_coverage_profiles FOREIGN KEY (profile_id) REFERENCES public.coverage_profiles(id) ON DELETE CASCADE;


--
-- Name: coverage_profile_languages fk_coverage_profile_languages_language_tag_language_tags; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.coverage_profile_languages
    ADD CONSTRAINT fk_coverage_profile_languages_language_tag_language_tags FOREIGN KEY (language_tag) REFERENCES public.language_tags(tag) ON DELETE RESTRICT;


--
-- Name: coverage_profile_languages fk_coverage_profile_languages_profile_id_coverage_profiles; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.coverage_profile_languages
    ADD CONSTRAINT fk_coverage_profile_languages_profile_id_coverage_profiles FOREIGN KEY (profile_id) REFERENCES public.coverage_profiles(id) ON DELETE CASCADE;


--
-- Name: coverage_profile_source_polling_overrides fk_coverage_profile_source_polling_overrides_profile_id_4ac5; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.coverage_profile_source_polling_overrides
    ADD CONSTRAINT fk_coverage_profile_source_polling_overrides_profile_id_4ac5 FOREIGN KEY (profile_id) REFERENCES public.coverage_profiles(id) ON DELETE CASCADE;


--
-- Name: coverage_profile_source_polling_overrides fk_coverage_profile_source_polling_overrides_source_id_sources; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.coverage_profile_source_polling_overrides
    ADD CONSTRAINT fk_coverage_profile_source_polling_overrides_source_id_sources FOREIGN KEY (source_id) REFERENCES public.sources(id) ON DELETE RESTRICT;


--
-- Name: coverage_profile_source_types fk_coverage_profile_source_types_profile_id_coverage_profiles; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.coverage_profile_source_types
    ADD CONSTRAINT fk_coverage_profile_source_types_profile_id_coverage_profiles FOREIGN KEY (profile_id) REFERENCES public.coverage_profiles(id) ON DELETE CASCADE;


--
-- Name: coverage_profile_source_types fk_coverage_profile_source_types_source_type_slug_source_types; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.coverage_profile_source_types
    ADD CONSTRAINT fk_coverage_profile_source_types_source_type_slug_source_types FOREIGN KEY (source_type_slug) REFERENCES public.source_types(slug) ON DELETE RESTRICT;


--
-- Name: coverage_profile_sources fk_coverage_profile_sources_profile_id_coverage_profiles; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.coverage_profile_sources
    ADD CONSTRAINT fk_coverage_profile_sources_profile_id_coverage_profiles FOREIGN KEY (profile_id) REFERENCES public.coverage_profiles(id) ON DELETE CASCADE;


--
-- Name: coverage_profile_sources fk_coverage_profile_sources_source_id_sources; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.coverage_profile_sources
    ADD CONSTRAINT fk_coverage_profile_sources_source_id_sources FOREIGN KEY (source_id) REFERENCES public.sources(id) ON DELETE RESTRICT;


--
-- Name: coverage_profile_topics fk_coverage_profile_topics_profile_id_coverage_profiles; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.coverage_profile_topics
    ADD CONSTRAINT fk_coverage_profile_topics_profile_id_coverage_profiles FOREIGN KEY (profile_id) REFERENCES public.coverage_profiles(id) ON DELETE CASCADE;


--
-- Name: coverage_profile_topics fk_coverage_profile_topics_topic_id_topics; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.coverage_profile_topics
    ADD CONSTRAINT fk_coverage_profile_topics_topic_id_topics FOREIGN KEY (topic_id) REFERENCES public.topics(id) ON DELETE RESTRICT;


--
-- Name: coverage_profile_translation_targets fk_coverage_profile_translation_targets_language_tag_la_304e; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.coverage_profile_translation_targets
    ADD CONSTRAINT fk_coverage_profile_translation_targets_language_tag_la_304e FOREIGN KEY (language_tag) REFERENCES public.language_tags(tag) ON DELETE RESTRICT;


--
-- Name: coverage_profile_translation_targets fk_coverage_profile_translation_targets_profile_id_cove_74c2; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.coverage_profile_translation_targets
    ADD CONSTRAINT fk_coverage_profile_translation_targets_profile_id_cove_74c2 FOREIGN KEY (profile_id) REFERENCES public.coverage_profiles(id) ON DELETE CASCADE;


--
-- Name: document_entities fk_document_entities_classification_run_id_classification_runs; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.document_entities
    ADD CONSTRAINT fk_document_entities_classification_run_id_classification_runs FOREIGN KEY (classification_run_id) REFERENCES public.classification_runs(id) ON DELETE SET NULL;


--
-- Name: document_entities fk_document_entities_document_id_documents; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.document_entities
    ADD CONSTRAINT fk_document_entities_document_id_documents FOREIGN KEY (document_id) REFERENCES public.documents(id) ON DELETE CASCADE;


--
-- Name: document_entities fk_document_entities_entity_id_entities; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.document_entities
    ADD CONSTRAINT fk_document_entities_entity_id_entities FOREIGN KEY (entity_id) REFERENCES public.entities(id) ON DELETE RESTRICT;


--
-- Name: document_geographies fk_document_geographies_classification_run_id_classific_8c61; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.document_geographies
    ADD CONSTRAINT fk_document_geographies_classification_run_id_classific_8c61 FOREIGN KEY (classification_run_id) REFERENCES public.classification_runs(id) ON DELETE SET NULL;


--
-- Name: document_geographies fk_document_geographies_document_id_documents; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.document_geographies
    ADD CONSTRAINT fk_document_geographies_document_id_documents FOREIGN KEY (document_id) REFERENCES public.documents(id) ON DELETE CASCADE;


--
-- Name: document_geographies fk_document_geographies_geography_id_geographies; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.document_geographies
    ADD CONSTRAINT fk_document_geographies_geography_id_geographies FOREIGN KEY (geography_id) REFERENCES public.geographies(id) ON DELETE RESTRICT;


--
-- Name: document_topics fk_document_topics_classification_run_id_classification_runs; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.document_topics
    ADD CONSTRAINT fk_document_topics_classification_run_id_classification_runs FOREIGN KEY (classification_run_id) REFERENCES public.classification_runs(id) ON DELETE SET NULL;


--
-- Name: document_topics fk_document_topics_document_id_documents; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.document_topics
    ADD CONSTRAINT fk_document_topics_document_id_documents FOREIGN KEY (document_id) REFERENCES public.documents(id) ON DELETE CASCADE;


--
-- Name: document_topics fk_document_topics_topic_id_topics; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.document_topics
    ADD CONSTRAINT fk_document_topics_topic_id_topics FOREIGN KEY (topic_id) REFERENCES public.topics(id) ON DELETE RESTRICT;


--
-- Name: document_type_assignments fk_document_type_assignments_classification_run_id_clas_558d; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.document_type_assignments
    ADD CONSTRAINT fk_document_type_assignments_classification_run_id_clas_558d FOREIGN KEY (classification_run_id) REFERENCES public.classification_runs(id) ON DELETE SET NULL;


--
-- Name: document_type_assignments fk_document_type_assignments_document_id_documents; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.document_type_assignments
    ADD CONSTRAINT fk_document_type_assignments_document_id_documents FOREIGN KEY (document_id) REFERENCES public.documents(id) ON DELETE CASCADE;


--
-- Name: document_type_assignments fk_document_type_assignments_document_type_id_document_types; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.document_type_assignments
    ADD CONSTRAINT fk_document_type_assignments_document_type_id_document_types FOREIGN KEY (document_type_id) REFERENCES public.document_types(id) ON DELETE RESTRICT;


--
-- Name: document_types fk_document_types_parent_id_document_types; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.document_types
    ADD CONSTRAINT fk_document_types_parent_id_document_types FOREIGN KEY (parent_id) REFERENCES public.document_types(id) ON DELETE RESTRICT;


--
-- Name: document_versions fk_document_versions_content_format_content_formats_slug; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.document_versions
    ADD CONSTRAINT fk_document_versions_content_format_content_formats_slug FOREIGN KEY (content_format) REFERENCES public.content_formats(slug) ON DELETE RESTRICT;


--
-- Name: document_versions fk_document_versions_document_id_documents; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.document_versions
    ADD CONSTRAINT fk_document_versions_document_id_documents FOREIGN KEY (document_id) REFERENCES public.documents(id) ON DELETE CASCADE;


--
-- Name: document_versions fk_document_versions_language_language_tags_tag; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.document_versions
    ADD CONSTRAINT fk_document_versions_language_language_tags_tag FOREIGN KEY (language) REFERENCES public.language_tags(tag) ON DELETE RESTRICT;


--
-- Name: documents fk_documents_content_format_content_formats_slug; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.documents
    ADD CONSTRAINT fk_documents_content_format_content_formats_slug FOREIGN KEY (content_format) REFERENCES public.content_formats(slug) ON DELETE RESTRICT;


--
-- Name: documents fk_documents_ingestion_format_endpoint_formats_slug; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.documents
    ADD CONSTRAINT fk_documents_ingestion_format_endpoint_formats_slug FOREIGN KEY (ingestion_format) REFERENCES public.endpoint_formats(slug) ON DELETE RESTRICT;


--
-- Name: documents fk_documents_language_language_tags_tag; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.documents
    ADD CONSTRAINT fk_documents_language_language_tags_tag FOREIGN KEY (language) REFERENCES public.language_tags(tag) ON DELETE RESTRICT;


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
-- Name: entity_aliases fk_entity_aliases_entity_id_entities; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.entity_aliases
    ADD CONSTRAINT fk_entity_aliases_entity_id_entities FOREIGN KEY (entity_id) REFERENCES public.entities(id) ON DELETE CASCADE;


--
-- Name: entity_aliases fk_entity_aliases_language_language_tags_tag; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.entity_aliases
    ADD CONSTRAINT fk_entity_aliases_language_language_tags_tag FOREIGN KEY (language) REFERENCES public.language_tags(tag) ON DELETE RESTRICT;


--
-- Name: entity_geographies fk_entity_geographies_assignment_method_semantic_assign_b32a; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.entity_geographies
    ADD CONSTRAINT fk_entity_geographies_assignment_method_semantic_assign_b32a FOREIGN KEY (assignment_method) REFERENCES public.semantic_assignment_methods(slug) ON DELETE RESTRICT;


--
-- Name: entity_geographies fk_entity_geographies_entity_id_entities; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.entity_geographies
    ADD CONSTRAINT fk_entity_geographies_entity_id_entities FOREIGN KEY (entity_id) REFERENCES public.entities(id) ON DELETE RESTRICT;


--
-- Name: entity_geographies fk_entity_geographies_geography_id_geographies; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.entity_geographies
    ADD CONSTRAINT fk_entity_geographies_geography_id_geographies FOREIGN KEY (geography_id) REFERENCES public.geographies(id) ON DELETE RESTRICT;


--
-- Name: entity_geographies fk_entity_geographies_relationship_type_entity_geograph_a3d4; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.entity_geographies
    ADD CONSTRAINT fk_entity_geographies_relationship_type_entity_geograph_a3d4 FOREIGN KEY (relationship_type) REFERENCES public.entity_geography_relationship_types(slug) ON DELETE RESTRICT;


--
-- Name: entity_geography_relationship_type_external_mappings fk_entity_geography_relationship_type_external_mappings_5b8c; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.entity_geography_relationship_type_external_mappings
    ADD CONSTRAINT fk_entity_geography_relationship_type_external_mappings_5b8c FOREIGN KEY (relationship_type) REFERENCES public.entity_geography_relationship_types(slug) ON DELETE RESTRICT;


--
-- Name: entity_geography_relationship_type_external_mappings fk_entity_geography_type_mappings_relation_kind; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.entity_geography_relationship_type_external_mappings
    ADD CONSTRAINT fk_entity_geography_type_mappings_relation_kind FOREIGN KEY (mapping_relation, resource_kind) REFERENCES public.semantic_mapping_relations(slug, applicable_resource_kind) ON DELETE RESTRICT;


--
-- Name: entity_geography_relationship_type_external_mappings fk_entity_geography_type_mappings_resource_kind; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.entity_geography_relationship_type_external_mappings
    ADD CONSTRAINT fk_entity_geography_type_mappings_resource_kind FOREIGN KEY (external_resource_id, resource_kind) REFERENCES public.external_semantic_resources(id, resource_kind) ON DELETE RESTRICT;


--
-- Name: entity_type_assignments fk_entity_type_assignments_assignment_method_semantic_a_5725; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.entity_type_assignments
    ADD CONSTRAINT fk_entity_type_assignments_assignment_method_semantic_a_5725 FOREIGN KEY (assignment_method) REFERENCES public.semantic_assignment_methods(slug) ON DELETE RESTRICT;


--
-- Name: entity_type_assignments fk_entity_type_assignments_entity_id_entities; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.entity_type_assignments
    ADD CONSTRAINT fk_entity_type_assignments_entity_id_entities FOREIGN KEY (entity_id) REFERENCES public.entities(id) ON DELETE RESTRICT;


--
-- Name: entity_type_assignments fk_entity_type_assignments_entity_type_id_entity_types; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.entity_type_assignments
    ADD CONSTRAINT fk_entity_type_assignments_entity_type_id_entity_types FOREIGN KEY (entity_type_id) REFERENCES public.entity_types(id) ON DELETE RESTRICT;


--
-- Name: entity_type_external_mappings fk_entity_type_external_mappings_entity_type_id_entity_types; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.entity_type_external_mappings
    ADD CONSTRAINT fk_entity_type_external_mappings_entity_type_id_entity_types FOREIGN KEY (entity_type_id) REFERENCES public.entity_types(id) ON DELETE RESTRICT;


--
-- Name: entity_type_external_mappings fk_entity_type_external_mappings_relation_kind; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.entity_type_external_mappings
    ADD CONSTRAINT fk_entity_type_external_mappings_relation_kind FOREIGN KEY (mapping_relation, resource_kind) REFERENCES public.semantic_mapping_relations(slug, applicable_resource_kind) ON DELETE RESTRICT;


--
-- Name: entity_type_external_mappings fk_entity_type_external_mappings_resource_kind; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.entity_type_external_mappings
    ADD CONSTRAINT fk_entity_type_external_mappings_resource_kind FOREIGN KEY (external_resource_id, resource_kind) REFERENCES public.external_semantic_resources(id, resource_kind) ON DELETE RESTRICT;


--
-- Name: entity_type_hierarchy_edges fk_entity_type_hierarchy_edges_child_entity_type_id_ent_93c4; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.entity_type_hierarchy_edges
    ADD CONSTRAINT fk_entity_type_hierarchy_edges_child_entity_type_id_ent_93c4 FOREIGN KEY (child_entity_type_id) REFERENCES public.entity_types(id) ON DELETE RESTRICT;


--
-- Name: entity_type_hierarchy_edges fk_entity_type_hierarchy_edges_parent_entity_type_id_en_573f; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.entity_type_hierarchy_edges
    ADD CONSTRAINT fk_entity_type_hierarchy_edges_parent_entity_type_id_en_573f FOREIGN KEY (parent_entity_type_id) REFERENCES public.entity_types(id) ON DELETE RESTRICT;


--
-- Name: external_semantic_resources fk_external_semantic_resources_resource_kind_external_s_ec79; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.external_semantic_resources
    ADD CONSTRAINT fk_external_semantic_resources_resource_kind_external_s_ec79 FOREIGN KEY (resource_kind) REFERENCES public.external_semantic_resource_kinds(slug) ON DELETE RESTRICT;


--
-- Name: external_semantic_resources fk_external_semantic_resources_scheme_id_external_seman_a194; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.external_semantic_resources
    ADD CONSTRAINT fk_external_semantic_resources_scheme_id_external_seman_a194 FOREIGN KEY (scheme_id) REFERENCES public.external_semantic_schemes(id) ON DELETE RESTRICT;


--
-- Name: external_semantic_schemes fk_external_semantic_schemes_authority_slug_external_se_a7a6; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.external_semantic_schemes
    ADD CONSTRAINT fk_external_semantic_schemes_authority_slug_external_se_a7a6 FOREIGN KEY (authority_slug) REFERENCES public.external_semantic_authorities(slug) ON DELETE RESTRICT;


--
-- Name: geographies fk_geographies_parent_id_geographies; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.geographies
    ADD CONSTRAINT fk_geographies_parent_id_geographies FOREIGN KEY (parent_id) REFERENCES public.geographies(id) ON DELETE RESTRICT;


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
-- Name: intelligence_calendar_event_aliases fk_intelligence_calendar_event_aliases_event_id_intelli_8867; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.intelligence_calendar_event_aliases
    ADD CONSTRAINT fk_intelligence_calendar_event_aliases_event_id_intelli_8867 FOREIGN KEY (event_id) REFERENCES public.intelligence_calendar_events(id) ON DELETE CASCADE;


--
-- Name: intelligence_calendar_event_aliases fk_intelligence_calendar_event_aliases_language_tag_lan_cc60; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.intelligence_calendar_event_aliases
    ADD CONSTRAINT fk_intelligence_calendar_event_aliases_language_tag_lan_cc60 FOREIGN KEY (language_tag) REFERENCES public.language_tags(tag) ON DELETE RESTRICT;


--
-- Name: intelligence_calendar_event_coverage_policies fk_intelligence_calendar_event_coverage_policies_event__c662; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.intelligence_calendar_event_coverage_policies
    ADD CONSTRAINT fk_intelligence_calendar_event_coverage_policies_event__c662 FOREIGN KEY (event_id) REFERENCES public.intelligence_calendar_events(id) ON DELETE CASCADE;


--
-- Name: intelligence_calendar_event_coverage_policies fk_intelligence_calendar_event_coverage_policies_profil_be9c; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.intelligence_calendar_event_coverage_policies
    ADD CONSTRAINT fk_intelligence_calendar_event_coverage_policies_profil_be9c FOREIGN KEY (profile_id) REFERENCES public.coverage_profiles(id) ON DELETE RESTRICT;


--
-- Name: intelligence_calendar_event_documents fk_intelligence_calendar_event_documents_document_id_documents; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.intelligence_calendar_event_documents
    ADD CONSTRAINT fk_intelligence_calendar_event_documents_document_id_documents FOREIGN KEY (document_id) REFERENCES public.documents(id) ON DELETE RESTRICT;


--
-- Name: intelligence_calendar_event_documents fk_intelligence_calendar_event_documents_event_id_intel_12c2; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.intelligence_calendar_event_documents
    ADD CONSTRAINT fk_intelligence_calendar_event_documents_event_id_intel_12c2 FOREIGN KEY (event_id) REFERENCES public.intelligence_calendar_events(id) ON DELETE CASCADE;


--
-- Name: intelligence_calendar_event_documents fk_intelligence_calendar_event_documents_evidence_id_in_421a; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.intelligence_calendar_event_documents
    ADD CONSTRAINT fk_intelligence_calendar_event_documents_evidence_id_in_421a FOREIGN KEY (evidence_id) REFERENCES public.intelligence_calendar_event_evidence(id) ON DELETE RESTRICT;


--
-- Name: intelligence_calendar_event_entities fk_intelligence_calendar_event_entities_entity_id_entities; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.intelligence_calendar_event_entities
    ADD CONSTRAINT fk_intelligence_calendar_event_entities_entity_id_entities FOREIGN KEY (entity_id) REFERENCES public.entities(id) ON DELETE RESTRICT;


--
-- Name: intelligence_calendar_event_entities fk_intelligence_calendar_event_entities_event_id_intell_eb68; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.intelligence_calendar_event_entities
    ADD CONSTRAINT fk_intelligence_calendar_event_entities_event_id_intell_eb68 FOREIGN KEY (event_id) REFERENCES public.intelligence_calendar_events(id) ON DELETE CASCADE;


--
-- Name: intelligence_calendar_event_entities fk_intelligence_calendar_event_entities_evidence_id_int_ef35; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.intelligence_calendar_event_entities
    ADD CONSTRAINT fk_intelligence_calendar_event_entities_evidence_id_int_ef35 FOREIGN KEY (evidence_id) REFERENCES public.intelligence_calendar_event_evidence(id) ON DELETE RESTRICT;


--
-- Name: intelligence_calendar_event_evidence fk_intelligence_calendar_event_evidence_document_id_documents; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.intelligence_calendar_event_evidence
    ADD CONSTRAINT fk_intelligence_calendar_event_evidence_document_id_documents FOREIGN KEY (document_id) REFERENCES public.documents(id) ON DELETE RESTRICT;


--
-- Name: intelligence_calendar_event_evidence fk_intelligence_calendar_event_evidence_event_id_intell_5a59; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.intelligence_calendar_event_evidence
    ADD CONSTRAINT fk_intelligence_calendar_event_evidence_event_id_intell_5a59 FOREIGN KEY (event_id) REFERENCES public.intelligence_calendar_events(id) ON DELETE CASCADE;


--
-- Name: intelligence_calendar_event_evidence fk_intelligence_calendar_event_evidence_language_tag_la_f8ed; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.intelligence_calendar_event_evidence
    ADD CONSTRAINT fk_intelligence_calendar_event_evidence_language_tag_la_f8ed FOREIGN KEY (language_tag) REFERENCES public.language_tags(tag) ON DELETE RESTRICT;


--
-- Name: intelligence_calendar_event_evidence fk_intelligence_calendar_event_evidence_source_id_sources; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.intelligence_calendar_event_evidence
    ADD CONSTRAINT fk_intelligence_calendar_event_evidence_source_id_sources FOREIGN KEY (source_id) REFERENCES public.sources(id) ON DELETE RESTRICT;


--
-- Name: intelligence_calendar_event_geographies fk_intelligence_calendar_event_geographies_event_id_int_f4e8; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.intelligence_calendar_event_geographies
    ADD CONSTRAINT fk_intelligence_calendar_event_geographies_event_id_int_f4e8 FOREIGN KEY (event_id) REFERENCES public.intelligence_calendar_events(id) ON DELETE CASCADE;


--
-- Name: intelligence_calendar_event_geographies fk_intelligence_calendar_event_geographies_evidence_id__ff42; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.intelligence_calendar_event_geographies
    ADD CONSTRAINT fk_intelligence_calendar_event_geographies_evidence_id__ff42 FOREIGN KEY (evidence_id) REFERENCES public.intelligence_calendar_event_evidence(id) ON DELETE RESTRICT;


--
-- Name: intelligence_calendar_event_geographies fk_intelligence_calendar_event_geographies_geography_id_30d7; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.intelligence_calendar_event_geographies
    ADD CONSTRAINT fk_intelligence_calendar_event_geographies_geography_id_30d7 FOREIGN KEY (geography_id) REFERENCES public.geographies(id) ON DELETE RESTRICT;


--
-- Name: intelligence_calendar_event_merge_history fk_intelligence_calendar_event_merge_history_evidence_i_3ae9; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.intelligence_calendar_event_merge_history
    ADD CONSTRAINT fk_intelligence_calendar_event_merge_history_evidence_i_3ae9 FOREIGN KEY (evidence_id) REFERENCES public.intelligence_calendar_event_evidence(id) ON DELETE RESTRICT;


--
-- Name: intelligence_calendar_event_merge_history fk_intelligence_calendar_event_merge_history_loser_even_c9fb; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.intelligence_calendar_event_merge_history
    ADD CONSTRAINT fk_intelligence_calendar_event_merge_history_loser_even_c9fb FOREIGN KEY (loser_event_id) REFERENCES public.intelligence_calendar_events(id) ON DELETE RESTRICT;


--
-- Name: intelligence_calendar_event_merge_history fk_intelligence_calendar_event_merge_history_winner_eve_1ede; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.intelligence_calendar_event_merge_history
    ADD CONSTRAINT fk_intelligence_calendar_event_merge_history_winner_eve_1ede FOREIGN KEY (winner_event_id) REFERENCES public.intelligence_calendar_events(id) ON DELETE RESTRICT;


--
-- Name: intelligence_calendar_event_monitors fk_intelligence_calendar_event_monitors_event_id_intell_4949; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.intelligence_calendar_event_monitors
    ADD CONSTRAINT fk_intelligence_calendar_event_monitors_event_id_intell_4949 FOREIGN KEY (event_id) REFERENCES public.intelligence_calendar_events(id) ON DELETE CASCADE;


--
-- Name: intelligence_calendar_event_monitors fk_intelligence_calendar_event_monitors_monitor_id_monitors; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.intelligence_calendar_event_monitors
    ADD CONSTRAINT fk_intelligence_calendar_event_monitors_monitor_id_monitors FOREIGN KEY (monitor_id) REFERENCES public.monitors(id) ON DELETE RESTRICT;


--
-- Name: intelligence_calendar_event_occurrences fk_intelligence_calendar_event_occurrences_event_id_int_4ce4; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.intelligence_calendar_event_occurrences
    ADD CONSTRAINT fk_intelligence_calendar_event_occurrences_event_id_int_4ce4 FOREIGN KEY (event_id) REFERENCES public.intelligence_calendar_events(id) ON DELETE CASCADE;


--
-- Name: intelligence_calendar_event_occurrences fk_intelligence_calendar_event_occurrences_recurrence_r_e258; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.intelligence_calendar_event_occurrences
    ADD CONSTRAINT fk_intelligence_calendar_event_occurrences_recurrence_r_e258 FOREIGN KEY (recurrence_rule_id) REFERENCES public.intelligence_calendar_event_recurrence_rules(id) ON DELETE RESTRICT;


--
-- Name: intelligence_calendar_event_recurrence_exceptions fk_intelligence_calendar_event_recurrence_exceptions_re_4c0f; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.intelligence_calendar_event_recurrence_exceptions
    ADD CONSTRAINT fk_intelligence_calendar_event_recurrence_exceptions_re_4c0f FOREIGN KEY (recurrence_rule_id) REFERENCES public.intelligence_calendar_event_recurrence_rules(id) ON DELETE CASCADE;


--
-- Name: intelligence_calendar_event_recurrence_rules fk_intelligence_calendar_event_recurrence_rules_event_i_61e6; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.intelligence_calendar_event_recurrence_rules
    ADD CONSTRAINT fk_intelligence_calendar_event_recurrence_rules_event_i_61e6 FOREIGN KEY (event_id) REFERENCES public.intelligence_calendar_events(id) ON DELETE CASCADE;


--
-- Name: intelligence_calendar_event_revisions fk_intelligence_calendar_event_revisions_event_id_intel_34bc; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.intelligence_calendar_event_revisions
    ADD CONSTRAINT fk_intelligence_calendar_event_revisions_event_id_intel_34bc FOREIGN KEY (event_id) REFERENCES public.intelligence_calendar_events(id) ON DELETE CASCADE;


--
-- Name: intelligence_calendar_event_revisions fk_intelligence_calendar_event_revisions_original_langu_c709; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.intelligence_calendar_event_revisions
    ADD CONSTRAINT fk_intelligence_calendar_event_revisions_original_langu_c709 FOREIGN KEY (original_language_tag) REFERENCES public.language_tags(tag) ON DELETE RESTRICT;


--
-- Name: intelligence_calendar_event_sources fk_intelligence_calendar_event_sources_event_id_intelli_26e9; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.intelligence_calendar_event_sources
    ADD CONSTRAINT fk_intelligence_calendar_event_sources_event_id_intelli_26e9 FOREIGN KEY (event_id) REFERENCES public.intelligence_calendar_events(id) ON DELETE CASCADE;


--
-- Name: intelligence_calendar_event_sources fk_intelligence_calendar_event_sources_evidence_id_inte_4e77; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.intelligence_calendar_event_sources
    ADD CONSTRAINT fk_intelligence_calendar_event_sources_evidence_id_inte_4e77 FOREIGN KEY (evidence_id) REFERENCES public.intelligence_calendar_event_evidence(id) ON DELETE RESTRICT;


--
-- Name: intelligence_calendar_event_sources fk_intelligence_calendar_event_sources_source_id_sources; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.intelligence_calendar_event_sources
    ADD CONSTRAINT fk_intelligence_calendar_event_sources_source_id_sources FOREIGN KEY (source_id) REFERENCES public.sources(id) ON DELETE RESTRICT;


--
-- Name: intelligence_calendar_event_state_transitions fk_intelligence_calendar_event_state_transitions_event__92c5; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.intelligence_calendar_event_state_transitions
    ADD CONSTRAINT fk_intelligence_calendar_event_state_transitions_event__92c5 FOREIGN KEY (event_id) REFERENCES public.intelligence_calendar_events(id) ON DELETE CASCADE;


--
-- Name: intelligence_calendar_event_state_transitions fk_intelligence_calendar_event_state_transitions_eviden_6af0; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.intelligence_calendar_event_state_transitions
    ADD CONSTRAINT fk_intelligence_calendar_event_state_transitions_eviden_6af0 FOREIGN KEY (evidence_id) REFERENCES public.intelligence_calendar_event_evidence(id) ON DELETE RESTRICT;


--
-- Name: intelligence_calendar_event_topics fk_intelligence_calendar_event_topics_event_id_intellig_c547; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.intelligence_calendar_event_topics
    ADD CONSTRAINT fk_intelligence_calendar_event_topics_event_id_intellig_c547 FOREIGN KEY (event_id) REFERENCES public.intelligence_calendar_events(id) ON DELETE CASCADE;


--
-- Name: intelligence_calendar_event_topics fk_intelligence_calendar_event_topics_evidence_id_intel_32ce; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.intelligence_calendar_event_topics
    ADD CONSTRAINT fk_intelligence_calendar_event_topics_evidence_id_intel_32ce FOREIGN KEY (evidence_id) REFERENCES public.intelligence_calendar_event_evidence(id) ON DELETE RESTRICT;


--
-- Name: intelligence_calendar_event_topics fk_intelligence_calendar_event_topics_topic_id_topics; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.intelligence_calendar_event_topics
    ADD CONSTRAINT fk_intelligence_calendar_event_topics_topic_id_topics FOREIGN KEY (topic_id) REFERENCES public.topics(id) ON DELETE RESTRICT;


--
-- Name: intelligence_calendar_events fk_intelligence_calendar_events_merged_into_event_id_in_143e; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.intelligence_calendar_events
    ADD CONSTRAINT fk_intelligence_calendar_events_merged_into_event_id_in_143e FOREIGN KEY (merged_into_event_id) REFERENCES public.intelligence_calendar_events(id) ON DELETE RESTRICT;


--
-- Name: intelligence_calendar_occurrence_policy_overrides fk_intelligence_calendar_occurrence_policy_overrides_oc_65ec; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.intelligence_calendar_occurrence_policy_overrides
    ADD CONSTRAINT fk_intelligence_calendar_occurrence_policy_overrides_oc_65ec FOREIGN KEY (occurrence_id) REFERENCES public.intelligence_calendar_event_occurrences(id) ON DELETE CASCADE;


--
-- Name: intelligence_calendar_occurrence_policy_overrides fk_intelligence_calendar_occurrence_policy_overrides_po_4c89; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.intelligence_calendar_occurrence_policy_overrides
    ADD CONSTRAINT fk_intelligence_calendar_occurrence_policy_overrides_po_4c89 FOREIGN KEY (policy_id) REFERENCES public.intelligence_calendar_event_coverage_policies(id) ON DELETE CASCADE;


--
-- Name: intelligence_calendar_occurrence_schedule_revisions fk_intelligence_calendar_occurrence_schedule_revisions__dd61; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.intelligence_calendar_occurrence_schedule_revisions
    ADD CONSTRAINT fk_intelligence_calendar_occurrence_schedule_revisions__dd61 FOREIGN KEY (occurrence_id) REFERENCES public.intelligence_calendar_event_occurrences(id) ON DELETE CASCADE;


--
-- Name: intelligence_calendar_occurrence_schedule_revisions fk_intelligence_calendar_occurrence_schedule_revisions__fc15; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.intelligence_calendar_occurrence_schedule_revisions
    ADD CONSTRAINT fk_intelligence_calendar_occurrence_schedule_revisions__fc15 FOREIGN KEY (original_language_tag) REFERENCES public.language_tags(tag) ON DELETE RESTRICT;


--
-- Name: intelligence_calendar_policy_content_formats fk_intelligence_calendar_policy_content_formats_content_eb04; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.intelligence_calendar_policy_content_formats
    ADD CONSTRAINT fk_intelligence_calendar_policy_content_formats_content_eb04 FOREIGN KEY (content_format_slug) REFERENCES public.content_formats(slug) ON DELETE RESTRICT;


--
-- Name: intelligence_calendar_policy_content_formats fk_intelligence_calendar_policy_content_formats_policy__1c33; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.intelligence_calendar_policy_content_formats
    ADD CONSTRAINT fk_intelligence_calendar_policy_content_formats_policy__1c33 FOREIGN KEY (policy_id) REFERENCES public.intelligence_calendar_event_coverage_policies(id) ON DELETE CASCADE;


--
-- Name: intelligence_calendar_policy_document_types fk_intelligence_calendar_policy_document_types_document_a6ec; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.intelligence_calendar_policy_document_types
    ADD CONSTRAINT fk_intelligence_calendar_policy_document_types_document_a6ec FOREIGN KEY (document_type_id) REFERENCES public.document_types(id) ON DELETE RESTRICT;


--
-- Name: intelligence_calendar_policy_document_types fk_intelligence_calendar_policy_document_types_policy_i_35fb; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.intelligence_calendar_policy_document_types
    ADD CONSTRAINT fk_intelligence_calendar_policy_document_types_policy_i_35fb FOREIGN KEY (policy_id) REFERENCES public.intelligence_calendar_event_coverage_policies(id) ON DELETE CASCADE;


--
-- Name: intelligence_calendar_policy_search_terms fk_intelligence_calendar_policy_search_terms_language_t_3961; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.intelligence_calendar_policy_search_terms
    ADD CONSTRAINT fk_intelligence_calendar_policy_search_terms_language_t_3961 FOREIGN KEY (language_tag) REFERENCES public.language_tags(tag) ON DELETE RESTRICT;


--
-- Name: intelligence_calendar_policy_search_terms fk_intelligence_calendar_policy_search_terms_policy_id__7125; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.intelligence_calendar_policy_search_terms
    ADD CONSTRAINT fk_intelligence_calendar_policy_search_terms_policy_id__7125 FOREIGN KEY (policy_id) REFERENCES public.intelligence_calendar_event_coverage_policies(id) ON DELETE CASCADE;


--
-- Name: intelligence_calendar_policy_watch_sources fk_intelligence_calendar_policy_watch_sources_policy_id_f86d; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.intelligence_calendar_policy_watch_sources
    ADD CONSTRAINT fk_intelligence_calendar_policy_watch_sources_policy_id_f86d FOREIGN KEY (policy_id) REFERENCES public.intelligence_calendar_event_coverage_policies(id) ON DELETE CASCADE;


--
-- Name: intelligence_calendar_policy_watch_sources fk_intelligence_calendar_policy_watch_sources_source_en_d5b5; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.intelligence_calendar_policy_watch_sources
    ADD CONSTRAINT fk_intelligence_calendar_policy_watch_sources_source_en_d5b5 FOREIGN KEY (source_endpoint_id) REFERENCES public.source_endpoints(id) ON DELETE RESTRICT;


--
-- Name: intelligence_calendar_policy_watch_sources fk_intelligence_calendar_policy_watch_sources_source_id_sources; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.intelligence_calendar_policy_watch_sources
    ADD CONSTRAINT fk_intelligence_calendar_policy_watch_sources_source_id_sources FOREIGN KEY (source_id) REFERENCES public.sources(id) ON DELETE RESTRICT;


--
-- Name: language_tag_aliases fk_language_tag_aliases_canonical_tag_language_tags; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.language_tag_aliases
    ADD CONSTRAINT fk_language_tag_aliases_canonical_tag_language_tags FOREIGN KEY (canonical_tag) REFERENCES public.language_tags(tag) ON DELETE CASCADE;


--
-- Name: monitor_alert_destinations fk_monitor_alert_destinations_destination_id_alert_destinations; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.monitor_alert_destinations
    ADD CONSTRAINT fk_monitor_alert_destinations_destination_id_alert_destinations FOREIGN KEY (destination_id) REFERENCES public.alert_destinations(id) ON DELETE RESTRICT;


--
-- Name: monitor_alert_destinations fk_monitor_alert_destinations_monitor_id_monitors; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.monitor_alert_destinations
    ADD CONSTRAINT fk_monitor_alert_destinations_monitor_id_monitors FOREIGN KEY (monitor_id) REFERENCES public.monitors(id) ON DELETE RESTRICT;


--
-- Name: monitor_evaluation_runs fk_monitor_evaluation_runs_document_id_documents; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.monitor_evaluation_runs
    ADD CONSTRAINT fk_monitor_evaluation_runs_document_id_documents FOREIGN KEY (document_id) REFERENCES public.documents(id) ON DELETE SET NULL;


--
-- Name: monitor_evaluation_runs fk_monitor_evaluation_runs_revision; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.monitor_evaluation_runs
    ADD CONSTRAINT fk_monitor_evaluation_runs_revision FOREIGN KEY (monitor_id, monitor_revision_id) REFERENCES public.monitor_revisions(monitor_id, id) ON DELETE RESTRICT;


--
-- Name: monitor_matches fk_monitor_matches_document_id_documents; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.monitor_matches
    ADD CONSTRAINT fk_monitor_matches_document_id_documents FOREIGN KEY (document_id) REFERENCES public.documents(id) ON DELETE CASCADE;


--
-- Name: monitor_matches fk_monitor_matches_first_evaluation_run; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.monitor_matches
    ADD CONSTRAINT fk_monitor_matches_first_evaluation_run FOREIGN KEY (monitor_id, first_evaluation_run_id) REFERENCES public.monitor_evaluation_runs(monitor_id, id) ON DELETE RESTRICT;


--
-- Name: monitor_matches fk_monitor_matches_first_revision; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.monitor_matches
    ADD CONSTRAINT fk_monitor_matches_first_revision FOREIGN KEY (monitor_id, first_monitor_revision_id) REFERENCES public.monitor_revisions(monitor_id, id) ON DELETE RESTRICT;


--
-- Name: monitor_matches fk_monitor_matches_last_evaluation_run; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.monitor_matches
    ADD CONSTRAINT fk_monitor_matches_last_evaluation_run FOREIGN KEY (monitor_id, last_evaluation_run_id) REFERENCES public.monitor_evaluation_runs(monitor_id, id) ON DELETE RESTRICT;


--
-- Name: monitor_matches fk_monitor_matches_last_revision; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.monitor_matches
    ADD CONSTRAINT fk_monitor_matches_last_revision FOREIGN KEY (monitor_id, last_monitor_revision_id) REFERENCES public.monitor_revisions(monitor_id, id) ON DELETE RESTRICT;


--
-- Name: monitor_matches fk_monitor_matches_monitor_id_monitors; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.monitor_matches
    ADD CONSTRAINT fk_monitor_matches_monitor_id_monitors FOREIGN KEY (monitor_id) REFERENCES public.monitors(id) ON DELETE CASCADE;


--
-- Name: monitor_revision_content_formats fk_monitor_revision_content_formats_content_format_slug_43bc; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.monitor_revision_content_formats
    ADD CONSTRAINT fk_monitor_revision_content_formats_content_format_slug_43bc FOREIGN KEY (content_format_slug) REFERENCES public.content_formats(slug) ON DELETE RESTRICT;


--
-- Name: monitor_revision_content_formats fk_monitor_revision_content_formats_revision_id_monitor_75cb; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.monitor_revision_content_formats
    ADD CONSTRAINT fk_monitor_revision_content_formats_revision_id_monitor_75cb FOREIGN KEY (revision_id) REFERENCES public.monitor_revisions(id) ON DELETE CASCADE;


--
-- Name: monitor_revision_document_types fk_monitor_revision_document_types_document_type_id_doc_62ae; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.monitor_revision_document_types
    ADD CONSTRAINT fk_monitor_revision_document_types_document_type_id_doc_62ae FOREIGN KEY (document_type_id) REFERENCES public.document_types(id) ON DELETE RESTRICT;


--
-- Name: monitor_revision_document_types fk_monitor_revision_document_types_revision_id_monitor__1e9e; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.monitor_revision_document_types
    ADD CONSTRAINT fk_monitor_revision_document_types_revision_id_monitor__1e9e FOREIGN KEY (revision_id) REFERENCES public.monitor_revisions(id) ON DELETE CASCADE;


--
-- Name: monitor_revision_entities fk_monitor_revision_entities_entity_id_entities; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.monitor_revision_entities
    ADD CONSTRAINT fk_monitor_revision_entities_entity_id_entities FOREIGN KEY (entity_id) REFERENCES public.entities(id) ON DELETE RESTRICT;


--
-- Name: monitor_revision_entities fk_monitor_revision_entities_revision_id_monitor_revisions; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.monitor_revision_entities
    ADD CONSTRAINT fk_monitor_revision_entities_revision_id_monitor_revisions FOREIGN KEY (revision_id) REFERENCES public.monitor_revisions(id) ON DELETE CASCADE;


--
-- Name: monitor_revision_entity_roles fk_monitor_revision_entity_roles_revision_id_monitor_revisions; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.monitor_revision_entity_roles
    ADD CONSTRAINT fk_monitor_revision_entity_roles_revision_id_monitor_revisions FOREIGN KEY (revision_id) REFERENCES public.monitor_revisions(id) ON DELETE CASCADE;


--
-- Name: monitor_revision_geographies fk_monitor_revision_geographies_geography_id_geographies; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.monitor_revision_geographies
    ADD CONSTRAINT fk_monitor_revision_geographies_geography_id_geographies FOREIGN KEY (geography_id) REFERENCES public.geographies(id) ON DELETE RESTRICT;


--
-- Name: monitor_revision_geographies fk_monitor_revision_geographies_revision_id_monitor_revisions; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.monitor_revision_geographies
    ADD CONSTRAINT fk_monitor_revision_geographies_revision_id_monitor_revisions FOREIGN KEY (revision_id) REFERENCES public.monitor_revisions(id) ON DELETE CASCADE;


--
-- Name: monitor_revision_languages fk_monitor_revision_languages_language_tag_language_tags; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.monitor_revision_languages
    ADD CONSTRAINT fk_monitor_revision_languages_language_tag_language_tags FOREIGN KEY (language_tag) REFERENCES public.language_tags(tag) ON DELETE RESTRICT;


--
-- Name: monitor_revision_languages fk_monitor_revision_languages_revision_id_monitor_revisions; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.monitor_revision_languages
    ADD CONSTRAINT fk_monitor_revision_languages_revision_id_monitor_revisions FOREIGN KEY (revision_id) REFERENCES public.monitor_revisions(id) ON DELETE CASCADE;


--
-- Name: monitor_revision_source_types fk_monitor_revision_source_types_revision_id_monitor_revisions; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.monitor_revision_source_types
    ADD CONSTRAINT fk_monitor_revision_source_types_revision_id_monitor_revisions FOREIGN KEY (revision_id) REFERENCES public.monitor_revisions(id) ON DELETE CASCADE;


--
-- Name: monitor_revision_source_types fk_monitor_revision_source_types_source_type_slug_source_types; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.monitor_revision_source_types
    ADD CONSTRAINT fk_monitor_revision_source_types_source_type_slug_source_types FOREIGN KEY (source_type_slug) REFERENCES public.source_types(slug) ON DELETE RESTRICT;


--
-- Name: monitor_revision_sources fk_monitor_revision_sources_revision_id_monitor_revisions; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.monitor_revision_sources
    ADD CONSTRAINT fk_monitor_revision_sources_revision_id_monitor_revisions FOREIGN KEY (revision_id) REFERENCES public.monitor_revisions(id) ON DELETE CASCADE;


--
-- Name: monitor_revision_sources fk_monitor_revision_sources_source_id_sources; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.monitor_revision_sources
    ADD CONSTRAINT fk_monitor_revision_sources_source_id_sources FOREIGN KEY (source_id) REFERENCES public.sources(id) ON DELETE RESTRICT;


--
-- Name: monitor_revision_topics fk_monitor_revision_topics_revision_id_monitor_revisions; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.monitor_revision_topics
    ADD CONSTRAINT fk_monitor_revision_topics_revision_id_monitor_revisions FOREIGN KEY (revision_id) REFERENCES public.monitor_revisions(id) ON DELETE CASCADE;


--
-- Name: monitor_revision_topics fk_monitor_revision_topics_topic_id_topics; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.monitor_revision_topics
    ADD CONSTRAINT fk_monitor_revision_topics_topic_id_topics FOREIGN KEY (topic_id) REFERENCES public.topics(id) ON DELETE RESTRICT;


--
-- Name: monitor_revisions fk_monitor_revisions_monitor_id_monitors; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.monitor_revisions
    ADD CONSTRAINT fk_monitor_revisions_monitor_id_monitors FOREIGN KEY (monitor_id) REFERENCES public.monitors(id) ON DELETE CASCADE;


--
-- Name: monitors fk_monitors_coverage_profile_id_coverage_profiles; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.monitors
    ADD CONSTRAINT fk_monitors_coverage_profile_id_coverage_profiles FOREIGN KEY (coverage_profile_id) REFERENCES public.coverage_profiles(id) ON DELETE RESTRICT;


--
-- Name: semantic_mapping_relations fk_semantic_mapping_relations_applicable_resource_kind__5a60; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.semantic_mapping_relations
    ADD CONSTRAINT fk_semantic_mapping_relations_applicable_resource_kind__5a60 FOREIGN KEY (applicable_resource_kind) REFERENCES public.external_semantic_resource_kinds(slug) ON DELETE RESTRICT;


--
-- Name: semantic_mapping_relations fk_semantic_mapping_relations_inverse_slug; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.semantic_mapping_relations
    ADD CONSTRAINT fk_semantic_mapping_relations_inverse_slug FOREIGN KEY (inverse_slug) REFERENCES public.semantic_mapping_relations(slug) ON DELETE RESTRICT;


--
-- Name: source_endpoints fk_source_endpoints_acquisition_method_methods_slug; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.source_endpoints
    ADD CONSTRAINT fk_source_endpoints_acquisition_method_methods_slug FOREIGN KEY (acquisition_method) REFERENCES public.acquisition_methods(slug) ON DELETE RESTRICT;


--
-- Name: source_endpoints fk_source_endpoints_endpoint_format_endpoint_formats_slug; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.source_endpoints
    ADD CONSTRAINT fk_source_endpoints_endpoint_format_endpoint_formats_slug FOREIGN KEY (endpoint_format) REFERENCES public.endpoint_formats(slug) ON DELETE RESTRICT;


--
-- Name: source_endpoints fk_source_endpoints_endpoint_type_endpoint_types_slug; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.source_endpoints
    ADD CONSTRAINT fk_source_endpoints_endpoint_type_endpoint_types_slug FOREIGN KEY (endpoint_type) REFERENCES public.endpoint_types(slug) ON DELETE RESTRICT;


--
-- Name: source_endpoints fk_source_endpoints_platform_platforms_slug; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.source_endpoints
    ADD CONSTRAINT fk_source_endpoints_platform_platforms_slug FOREIGN KEY (platform) REFERENCES public.platforms(slug) ON DELETE RESTRICT;


--
-- Name: source_endpoints fk_source_endpoints_source_id_sources; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.source_endpoints
    ADD CONSTRAINT fk_source_endpoints_source_id_sources FOREIGN KEY (source_id) REFERENCES public.sources(id) ON DELETE CASCADE;


--
-- Name: source_types fk_source_types_parent_id_source_types; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.source_types
    ADD CONSTRAINT fk_source_types_parent_id_source_types FOREIGN KEY (parent_id) REFERENCES public.source_types(id) ON DELETE RESTRICT;


--
-- Name: sources fk_sources_primary_language_language_tags_tag; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.sources
    ADD CONSTRAINT fk_sources_primary_language_language_tags_tag FOREIGN KEY (primary_language) REFERENCES public.language_tags(tag) ON DELETE RESTRICT;


--
-- Name: sources fk_sources_source_type_source_types_slug; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.sources
    ADD CONSTRAINT fk_sources_source_type_source_types_slug FOREIGN KEY (source_type) REFERENCES public.source_types(slug) ON DELETE RESTRICT;


--
-- Name: topics fk_topics_parent_id_topics; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.topics
    ADD CONSTRAINT fk_topics_parent_id_topics FOREIGN KEY (parent_id) REFERENCES public.topics(id) ON DELETE RESTRICT;


--
-- PostgreSQL database dump complete
--

\unrestrict CrmfOXF6l65Jgm3ilY5Mr100DMYapjJPSKgBJTKmlaq8hj4yvx0LAmc963Gp8Fc

