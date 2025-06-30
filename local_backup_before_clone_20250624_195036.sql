--
-- PostgreSQL database dump
--

-- Dumped from database version 15.13 (Homebrew)
-- Dumped by pg_dump version 16.9 (Homebrew)

-- Started on 2025-06-24 19:50:37 CDT

SET statement_timeout = 0;
SET lock_timeout = 0;
SET idle_in_transaction_session_timeout = 0;
SET client_encoding = 'UTF8';
SET standard_conforming_strings = on;
SELECT pg_catalog.set_config('search_path', '', false);
SET check_function_bodies = false;
SET xmloption = content;
SET client_min_messages = warning;
SET row_security = off;

DROP DATABASE IF EXISTS rally;
--
-- TOC entry 4185 (class 1262 OID 17197)
-- Name: rally; Type: DATABASE; Schema: -; Owner: -
--

CREATE DATABASE rally WITH TEMPLATE = template0 ENCODING = 'UTF8' LOCALE_PROVIDER = libc LOCALE = 'C';


\connect rally

SET statement_timeout = 0;
SET lock_timeout = 0;
SET idle_in_transaction_session_timeout = 0;
SET client_encoding = 'UTF8';
SET standard_conforming_strings = on;
SELECT pg_catalog.set_config('search_path', '', false);
SET check_function_bodies = false;
SET xmloption = content;
SET client_min_messages = warning;
SET row_security = off;

--
-- TOC entry 277 (class 1255 OID 46436)
-- Name: assign_player_teams_from_matches(); Type: FUNCTION; Schema: public; Owner: -
--

CREATE FUNCTION public.assign_player_teams_from_matches() RETURNS TABLE(player_id text, player_name text, old_team text, new_team text, match_count bigint, assignment_confidence text)
    LANGUAGE plpgsql
    AS $$
BEGIN
    RETURN QUERY
    WITH player_match_teams AS (
        SELECT 
            CASE 
                WHEN ms.home_player_1_id = p.tenniscores_player_id THEN 
                    COALESCE(tfm_home.database_series_format, ms.home_team)
                WHEN ms.home_player_2_id = p.tenniscores_player_id THEN 
                    COALESCE(tfm_home.database_series_format, ms.home_team)
                WHEN ms.away_player_1_id = p.tenniscores_player_id THEN 
                    COALESCE(tfm_away.database_series_format, ms.away_team)
                WHEN ms.away_player_2_id = p.tenniscores_player_id THEN 
                    COALESCE(tfm_away.database_series_format, ms.away_team)
            END as resolved_team,
            p.tenniscores_player_id,
            p.first_name || ' ' || p.last_name as full_name,
            t.team_name as current_team,
            COUNT(*) as team_match_count
        FROM players p
        LEFT JOIN teams t ON p.team_id = t.id
        JOIN match_scores ms ON (
            ms.home_player_1_id = p.tenniscores_player_id OR
            ms.home_player_2_id = p.tenniscores_player_id OR
            ms.away_player_1_id = p.tenniscores_player_id OR
            ms.away_player_2_id = p.tenniscores_player_id
        )
        LEFT JOIN team_format_mappings tfm_home ON tfm_home.user_input_format = ms.home_team AND tfm_home.is_active = TRUE
        LEFT JOIN team_format_mappings tfm_away ON tfm_away.user_input_format = ms.away_team AND tfm_away.is_active = TRUE
        WHERE p.is_active = TRUE
        GROUP BY p.tenniscores_player_id, full_name, current_team, resolved_team
    ),
    player_primary_teams AS (
        SELECT 
            tenniscores_player_id,
            full_name,
            current_team,
            resolved_team as primary_team,
            team_match_count,
            SUM(team_match_count) OVER (PARTITION BY tenniscores_player_id) as total_matches,
            ROW_NUMBER() OVER (
                PARTITION BY tenniscores_player_id 
                ORDER BY team_match_count DESC
            ) as team_rank
        FROM player_match_teams
    ),
    final_assignments AS (
        SELECT 
            tenniscores_player_id,
            full_name,
            current_team,
            primary_team,
            team_match_count,
            total_matches,
            CASE 
                WHEN team_match_count::FLOAT / total_matches > 0.8 THEN 'HIGH'
                WHEN team_match_count::FLOAT / total_matches > 0.6 THEN 'MEDIUM'
                WHEN team_match_count::FLOAT / total_matches > 0.4 THEN 'LOW'
                ELSE 'VERY_LOW'
            END as confidence
        FROM player_primary_teams
        WHERE team_rank = 1
    )
    SELECT 
        fa.tenniscores_player_id::TEXT,
        fa.full_name::TEXT,
        COALESCE(fa.current_team, 'UNASSIGNED')::TEXT,
        fa.primary_team::TEXT,
        fa.team_match_count,
        fa.confidence::TEXT
    FROM final_assignments fa
    WHERE fa.current_team IS NULL 
    OR fa.current_team != fa.primary_team
    ORDER BY fa.team_match_count DESC;
END;
$$;


--
-- TOC entry 278 (class 1255 OID 46437)
-- Name: auto_populate_player_id(); Type: FUNCTION; Schema: public; Owner: -
--

CREATE FUNCTION public.auto_populate_player_id() RETURNS trigger
    LANGUAGE plpgsql
    AS $$
            BEGIN
                IF NEW.player_id IS NULL THEN
                    NEW.player_id := validate_player_exists(NEW.player_name, NEW.series_id);
                    
                    IF NEW.player_id IS NULL THEN
                        RAISE EXCEPTION 'Cannot create availability record: Player "%" not found in series ID % (or player is inactive). Please verify player name and series are correct.',
                            NEW.player_name, NEW.series_id;
                    END IF;
                END IF;
                
                RETURN NEW;
            END;
            $$;


--
-- TOC entry 279 (class 1255 OID 46438)
-- Name: update_player_season_tracking_updated_at(); Type: FUNCTION; Schema: public; Owner: -
--

CREATE FUNCTION public.update_player_season_tracking_updated_at() RETURNS trigger
    LANGUAGE plpgsql
    AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$;


--
-- TOC entry 280 (class 1255 OID 46439)
-- Name: update_teams_updated_at_column(); Type: FUNCTION; Schema: public; Owner: -
--

CREATE FUNCTION public.update_teams_updated_at_column() RETURNS trigger
    LANGUAGE plpgsql
    AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$;


--
-- TOC entry 281 (class 1255 OID 46440)
-- Name: update_updated_at_column(); Type: FUNCTION; Schema: public; Owner: -
--

CREATE FUNCTION public.update_updated_at_column() RETURNS trigger
    LANGUAGE plpgsql
    AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$;


--
-- TOC entry 282 (class 1255 OID 46441)
-- Name: validate_player_exists(character varying, integer); Type: FUNCTION; Schema: public; Owner: -
--

CREATE FUNCTION public.validate_player_exists(p_player_name character varying, p_series_id integer) RETURNS integer
    LANGUAGE plpgsql
    AS $$
            DECLARE
                player_record_id INTEGER;
            BEGIN
                SELECT id INTO player_record_id
                FROM players 
                WHERE CONCAT(first_name, ' ', last_name) = p_player_name
                AND series_id = p_series_id
                AND is_active = true;
                
                RETURN player_record_id;
            END;
            $$;


--
-- TOC entry 283 (class 1255 OID 46442)
-- Name: validate_team_assignments(); Type: FUNCTION; Schema: public; Owner: -
--

CREATE FUNCTION public.validate_team_assignments() RETURNS TABLE(validation_type character varying, issue_count integer, description character varying)
    LANGUAGE plpgsql
    AS $$
    BEGIN
        -- Check for players with no team assignment who have matches
        RETURN QUERY
        SELECT 
            'UNASSIGNED_WITH_MATCHES'::VARCHAR,
            COUNT(*)::INTEGER,
            'Players with matches but no team assignment'::VARCHAR
        FROM players p
        WHERE p.team_id IS NULL 
        AND p.is_active = TRUE
        AND EXISTS (
            SELECT 1 FROM match_scores ms 
            WHERE ms.home_player_1_id = p.tenniscores_player_id
            OR ms.home_player_2_id = p.tenniscores_player_id
            OR ms.away_player_1_id = p.tenniscores_player_id
            OR ms.away_player_2_id = p.tenniscores_player_id
        );
        
        -- Check for mismatched team assignments
        RETURN QUERY
        WITH player_match_teams AS (
            SELECT 
                p.tenniscores_player_id,
                CASE 
                    WHEN ms.home_player_1_id = p.tenniscores_player_id THEN ms.home_team
                    WHEN ms.home_player_2_id = p.tenniscores_player_id THEN ms.home_team
                    WHEN ms.away_player_1_id = p.tenniscores_player_id THEN ms.away_team
                    WHEN ms.away_player_2_id = p.tenniscores_player_id THEN ms.away_team
                END as match_team,
                t.team_name as assigned_team,
                COUNT(*) as match_count
            FROM players p
            LEFT JOIN teams t ON p.team_id = t.id
            JOIN match_scores ms ON (
                ms.home_player_1_id = p.tenniscores_player_id OR
                ms.home_player_2_id = p.tenniscores_player_id OR
                ms.away_player_1_id = p.tenniscores_player_id OR
                ms.away_player_2_id = p.tenniscores_player_id
            )
            WHERE p.is_active = TRUE AND t.team_name IS NOT NULL
            GROUP BY p.tenniscores_player_id, assigned_team, match_team
        ),
        mismatched AS (
            SELECT tenniscores_player_id
            FROM player_match_teams
            WHERE assigned_team != match_team
            GROUP BY tenniscores_player_id
        )
        SELECT 
            'MISMATCHED_ASSIGNMENTS'::VARCHAR,
            COUNT(*)::INTEGER,
            'Players assigned to wrong team based on matches'::VARCHAR
        FROM mismatched;
        
        -- Check for empty teams
        RETURN QUERY
        SELECT 
            'EMPTY_TEAMS'::VARCHAR,
            COUNT(*)::INTEGER,
            'Teams with no active players'::VARCHAR
        FROM teams t
        WHERE NOT EXISTS (
            SELECT 1 FROM players p 
            WHERE p.team_id = t.id AND p.is_active = TRUE
        );
    END;
    $$;


SET default_tablespace = '';

SET default_table_access_method = heap;

--
-- TOC entry 216 (class 1259 OID 46443)
-- Name: activity_log; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.activity_log (
    id uuid NOT NULL,
    player_id integer,
    team_id integer,
    user_id integer,
    action_type character varying(255) NOT NULL,
    action_description text NOT NULL,
    related_id character varying(255),
    related_type character varying(100),
    ip_address character varying(45),
    user_agent text,
    extra_data text,
    "timestamp" timestamp with time zone NOT NULL
);


--
-- TOC entry 217 (class 1259 OID 46448)
-- Name: alembic_version; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.alembic_version (
    version_num character varying(32) NOT NULL
);


--
-- TOC entry 218 (class 1259 OID 46451)
-- Name: club_leagues; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.club_leagues (
    id integer NOT NULL,
    club_id integer NOT NULL,
    league_id integer NOT NULL,
    created_at timestamp with time zone DEFAULT CURRENT_TIMESTAMP
);


--
-- TOC entry 219 (class 1259 OID 46455)
-- Name: club_leagues_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.club_leagues_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- TOC entry 4186 (class 0 OID 0)
-- Dependencies: 219
-- Name: club_leagues_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.club_leagues_id_seq OWNED BY public.club_leagues.id;


--
-- TOC entry 220 (class 1259 OID 46456)
-- Name: clubs; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.clubs (
    id integer NOT NULL,
    name character varying(255) NOT NULL,
    updated_at timestamp with time zone DEFAULT CURRENT_TIMESTAMP,
    club_address character varying(500)
);


--
-- TOC entry 221 (class 1259 OID 46462)
-- Name: clubs_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.clubs_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- TOC entry 4187 (class 0 OID 0)
-- Dependencies: 221
-- Name: clubs_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.clubs_id_seq OWNED BY public.clubs.id;


--
-- TOC entry 222 (class 1259 OID 46463)
-- Name: leagues; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.leagues (
    id integer NOT NULL,
    league_id character varying(255) NOT NULL,
    league_name character varying(255) NOT NULL,
    league_url character varying(512),
    created_at timestamp with time zone DEFAULT CURRENT_TIMESTAMP,
    updated_at timestamp with time zone DEFAULT CURRENT_TIMESTAMP
);


--
-- TOC entry 223 (class 1259 OID 46470)
-- Name: leagues_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.leagues_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- TOC entry 4188 (class 0 OID 0)
-- Dependencies: 223
-- Name: leagues_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.leagues_id_seq OWNED BY public.leagues.id;


--
-- TOC entry 224 (class 1259 OID 46471)
-- Name: match_scores; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.match_scores (
    id integer NOT NULL,
    match_date date,
    home_team text,
    away_team text,
    home_player_1_id text,
    home_player_2_id text,
    away_player_1_id text,
    away_player_2_id text,
    scores text,
    winner text,
    created_at timestamp with time zone DEFAULT CURRENT_TIMESTAMP,
    league_id integer,
    home_team_id integer,
    away_team_id integer,
    CONSTRAINT match_scores_winner_check CHECK ((winner = ANY (ARRAY['home'::text, 'away'::text])))
);


--
-- TOC entry 225 (class 1259 OID 46478)
-- Name: match_scores_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.match_scores_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- TOC entry 4189 (class 0 OID 0)
-- Dependencies: 225
-- Name: match_scores_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.match_scores_id_seq OWNED BY public.match_scores.id;


--
-- TOC entry 226 (class 1259 OID 46479)
-- Name: players; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.players (
    id integer NOT NULL,
    email character varying(255),
    first_name character varying(255) NOT NULL,
    last_name character varying(255) NOT NULL,
    club_id integer NOT NULL,
    series_id integer NOT NULL,
    created_at timestamp with time zone DEFAULT CURRENT_TIMESTAMP,
    tenniscores_player_id character varying(255) NOT NULL,
    league_id integer NOT NULL,
    is_active boolean DEFAULT true,
    pti numeric(10,2),
    wins integer DEFAULT 0,
    losses integer DEFAULT 0,
    win_percentage numeric(5,2) DEFAULT 0.00,
    captain_status character varying(50),
    updated_at timestamp with time zone DEFAULT CURRENT_TIMESTAMP,
    career_wins integer DEFAULT 0,
    career_losses integer DEFAULT 0,
    career_matches integer DEFAULT 0,
    career_win_percentage numeric(5,2) DEFAULT 0.00,
    team_id integer
);


--
-- TOC entry 227 (class 1259 OID 46494)
-- Name: user_player_associations; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.user_player_associations (
    user_id integer NOT NULL,
    is_primary boolean DEFAULT false,
    created_at timestamp with time zone DEFAULT CURRENT_TIMESTAMP,
    tenniscores_player_id character varying(255) NOT NULL
);


--
-- TOC entry 228 (class 1259 OID 46499)
-- Name: users; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.users (
    id integer NOT NULL,
    email character varying(255) NOT NULL,
    password_hash character varying(255) NOT NULL,
    first_name character varying(255),
    last_name character varying(255),
    club_automation_password character varying(255),
    created_at timestamp with time zone DEFAULT CURRENT_TIMESTAMP,
    last_login timestamp with time zone,
    is_admin boolean DEFAULT false NOT NULL,
    ad_deuce_preference character varying(50),
    dominant_hand character varying(20),
    league_id integer,
    tenniscores_player_id character varying(255)
);


--
-- TOC entry 229 (class 1259 OID 46506)
-- Name: migration_validation; Type: VIEW; Schema: public; Owner: -
--

CREATE VIEW public.migration_validation AS
 SELECT 'users'::text AS table_name,
    count(*) AS record_count,
    'Authentication-only fields'::text AS description
   FROM public.users
UNION ALL
 SELECT 'players'::text AS table_name,
    count(*) AS record_count,
    'League-specific player records'::text AS description
   FROM public.players
UNION ALL
 SELECT 'user_player_associations'::text AS table_name,
    count(*) AS record_count,
    'User-to-player links'::text AS description
   FROM public.user_player_associations
UNION ALL
 SELECT 'match_scores'::text AS table_name,
    count(*) AS record_count,
    'With INTEGER league_id FK'::text AS description
   FROM public.match_scores
  WHERE (match_scores.league_id IS NOT NULL);


--
-- TOC entry 230 (class 1259 OID 46511)
-- Name: player_availability; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.player_availability (
    id integer NOT NULL,
    player_name character varying(255) NOT NULL,
    availability_status integer DEFAULT 3 NOT NULL,
    updated_at timestamp with time zone DEFAULT CURRENT_TIMESTAMP,
    series_id integer NOT NULL,
    match_date timestamp with time zone NOT NULL,
    player_id integer,
    notes text,
    CONSTRAINT match_date_must_be_midnight_utc CHECK (((date_part('hour'::text, (match_date AT TIME ZONE 'UTC'::text)) = (0)::double precision) AND (date_part('minute'::text, (match_date AT TIME ZONE 'UTC'::text)) = (0)::double precision) AND (date_part('second'::text, (match_date AT TIME ZONE 'UTC'::text)) = (0)::double precision))),
    CONSTRAINT valid_availability_status CHECK ((availability_status = ANY (ARRAY[1, 2, 3])))
);


--
-- TOC entry 231 (class 1259 OID 46520)
-- Name: player_availability_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.player_availability_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- TOC entry 4190 (class 0 OID 0)
-- Dependencies: 231
-- Name: player_availability_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.player_availability_id_seq OWNED BY public.player_availability.id;


--
-- TOC entry 232 (class 1259 OID 46521)
-- Name: player_history; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.player_history (
    id integer NOT NULL,
    series character varying(255),
    date date,
    end_pti numeric(10,2),
    created_at timestamp with time zone DEFAULT CURRENT_TIMESTAMP,
    league_id integer,
    player_id integer
);


--
-- TOC entry 233 (class 1259 OID 46525)
-- Name: player_history_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.player_history_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- TOC entry 4191 (class 0 OID 0)
-- Dependencies: 233
-- Name: player_history_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.player_history_id_seq OWNED BY public.player_history.id;


--
-- TOC entry 234 (class 1259 OID 46526)
-- Name: player_season_tracking; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.player_season_tracking (
    id integer NOT NULL,
    player_id character varying(255) NOT NULL,
    league_id integer,
    season_year integer NOT NULL,
    forced_byes integer DEFAULT 0,
    not_available integer DEFAULT 0,
    injury integer DEFAULT 0,
    created_at timestamp with time zone DEFAULT CURRENT_TIMESTAMP,
    updated_at timestamp with time zone DEFAULT CURRENT_TIMESTAMP
);


--
-- TOC entry 235 (class 1259 OID 46534)
-- Name: player_season_tracking_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.player_season_tracking_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- TOC entry 4192 (class 0 OID 0)
-- Dependencies: 235
-- Name: player_season_tracking_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.player_season_tracking_id_seq OWNED BY public.player_season_tracking.id;


--
-- TOC entry 236 (class 1259 OID 46535)
-- Name: poll_choices; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.poll_choices (
    id integer NOT NULL,
    poll_id integer,
    choice_text text NOT NULL
);


--
-- TOC entry 237 (class 1259 OID 46540)
-- Name: poll_choices_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.poll_choices_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- TOC entry 4193 (class 0 OID 0)
-- Dependencies: 237
-- Name: poll_choices_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.poll_choices_id_seq OWNED BY public.poll_choices.id;


--
-- TOC entry 238 (class 1259 OID 46541)
-- Name: poll_responses; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.poll_responses (
    id integer NOT NULL,
    poll_id integer,
    choice_id integer,
    player_id integer,
    responded_at timestamp with time zone DEFAULT now()
);


--
-- TOC entry 239 (class 1259 OID 46545)
-- Name: poll_responses_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.poll_responses_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- TOC entry 4194 (class 0 OID 0)
-- Dependencies: 239
-- Name: poll_responses_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.poll_responses_id_seq OWNED BY public.poll_responses.id;


--
-- TOC entry 240 (class 1259 OID 46546)
-- Name: polls; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.polls (
    id integer NOT NULL,
    team_id integer,
    created_by integer,
    question text NOT NULL,
    created_at timestamp with time zone DEFAULT now()
);


--
-- TOC entry 241 (class 1259 OID 46552)
-- Name: polls_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.polls_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- TOC entry 4195 (class 0 OID 0)
-- Dependencies: 241
-- Name: polls_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.polls_id_seq OWNED BY public.polls.id;


--
-- TOC entry 242 (class 1259 OID 46553)
-- Name: pro_lessons; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.pro_lessons (
    id integer NOT NULL,
    user_email character varying(255) NOT NULL,
    pro_id integer,
    lesson_date date NOT NULL,
    lesson_time time without time zone NOT NULL,
    focus_areas text NOT NULL,
    notes text,
    status character varying(50) DEFAULT 'requested'::character varying,
    created_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP,
    updated_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP
);


--
-- TOC entry 243 (class 1259 OID 46561)
-- Name: pro_lessons_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.pro_lessons_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- TOC entry 4196 (class 0 OID 0)
-- Dependencies: 243
-- Name: pro_lessons_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.pro_lessons_id_seq OWNED BY public.pro_lessons.id;


--
-- TOC entry 244 (class 1259 OID 46562)
-- Name: pros; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.pros (
    id integer NOT NULL,
    name character varying(255) NOT NULL,
    bio text,
    specialties text,
    hourly_rate numeric(6,2),
    image_url character varying(500),
    phone character varying(20),
    email character varying(255),
    is_active boolean DEFAULT true,
    created_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP,
    updated_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP
);


--
-- TOC entry 245 (class 1259 OID 46570)
-- Name: pros_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.pros_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- TOC entry 4197 (class 0 OID 0)
-- Dependencies: 245
-- Name: pros_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.pros_id_seq OWNED BY public.pros.id;


--
-- TOC entry 246 (class 1259 OID 46571)
-- Name: schedule; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.schedule (
    id integer NOT NULL,
    match_date date,
    match_time time without time zone,
    home_team text,
    away_team text,
    location text,
    created_at timestamp with time zone DEFAULT CURRENT_TIMESTAMP,
    league_id integer,
    home_team_id integer,
    away_team_id integer
);


--
-- TOC entry 247 (class 1259 OID 46577)
-- Name: schedule_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.schedule_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- TOC entry 4198 (class 0 OID 0)
-- Dependencies: 247
-- Name: schedule_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.schedule_id_seq OWNED BY public.schedule.id;


--
-- TOC entry 248 (class 1259 OID 46578)
-- Name: series; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.series (
    id integer NOT NULL,
    name character varying(255) NOT NULL,
    updated_at timestamp with time zone DEFAULT CURRENT_TIMESTAMP
);


--
-- TOC entry 249 (class 1259 OID 46582)
-- Name: series_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.series_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- TOC entry 4199 (class 0 OID 0)
-- Dependencies: 249
-- Name: series_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.series_id_seq OWNED BY public.series.id;


--
-- TOC entry 250 (class 1259 OID 46583)
-- Name: series_leagues; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.series_leagues (
    id integer NOT NULL,
    series_id integer NOT NULL,
    league_id integer NOT NULL,
    created_at timestamp with time zone DEFAULT CURRENT_TIMESTAMP
);


--
-- TOC entry 251 (class 1259 OID 46587)
-- Name: series_leagues_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.series_leagues_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- TOC entry 4200 (class 0 OID 0)
-- Dependencies: 251
-- Name: series_leagues_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.series_leagues_id_seq OWNED BY public.series_leagues.id;


--
-- TOC entry 252 (class 1259 OID 46588)
-- Name: series_name_mappings; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.series_name_mappings (
    id integer NOT NULL,
    league_id character varying(50) NOT NULL,
    user_series_name character varying(100) NOT NULL,
    database_series_name character varying(100) NOT NULL,
    created_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP,
    updated_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP
);


--
-- TOC entry 4201 (class 0 OID 0)
-- Dependencies: 252
-- Name: TABLE series_name_mappings; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON TABLE public.series_name_mappings IS 'Maps user-facing series names to database series names for each league';


--
-- TOC entry 4202 (class 0 OID 0)
-- Dependencies: 252
-- Name: COLUMN series_name_mappings.league_id; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.series_name_mappings.league_id IS 'League identifier (CNSWPL, NSTF, etc.)';


--
-- TOC entry 4203 (class 0 OID 0)
-- Dependencies: 252
-- Name: COLUMN series_name_mappings.user_series_name; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.series_name_mappings.user_series_name IS 'Series name as it appears in user session data';


--
-- TOC entry 4204 (class 0 OID 0)
-- Dependencies: 252
-- Name: COLUMN series_name_mappings.database_series_name; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.series_name_mappings.database_series_name IS 'Series name as stored in database';


--
-- TOC entry 253 (class 1259 OID 46593)
-- Name: series_name_mappings_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.series_name_mappings_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- TOC entry 4205 (class 0 OID 0)
-- Dependencies: 253
-- Name: series_name_mappings_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.series_name_mappings_id_seq OWNED BY public.series_name_mappings.id;


--
-- TOC entry 254 (class 1259 OID 46594)
-- Name: series_stats; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.series_stats (
    id integer NOT NULL,
    series character varying(255),
    team character varying(255),
    points integer,
    matches_won integer,
    matches_lost integer,
    matches_tied integer,
    lines_won integer,
    lines_lost integer,
    lines_for integer,
    lines_ret integer,
    sets_won integer,
    sets_lost integer,
    games_won integer,
    games_lost integer,
    created_at timestamp with time zone DEFAULT CURRENT_TIMESTAMP,
    league_id integer,
    team_id integer
);


--
-- TOC entry 255 (class 1259 OID 46600)
-- Name: series_stats_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.series_stats_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- TOC entry 4206 (class 0 OID 0)
-- Dependencies: 255
-- Name: series_stats_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.series_stats_id_seq OWNED BY public.series_stats.id;


--
-- TOC entry 256 (class 1259 OID 46601)
-- Name: team_format_mappings; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.team_format_mappings (
    id integer NOT NULL,
    league_id character varying(50) NOT NULL,
    user_input_format character varying(100) NOT NULL,
    database_series_format character varying(100) NOT NULL,
    mapping_type character varying(50) DEFAULT 'series_mapping'::character varying,
    description text,
    is_active boolean DEFAULT true,
    created_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP,
    updated_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP
);


--
-- TOC entry 4207 (class 0 OID 0)
-- Dependencies: 256
-- Name: TABLE team_format_mappings; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON TABLE public.team_format_mappings IS 'Comprehensive mapping of user-facing series formats to database series formats for all leagues';


--
-- TOC entry 4208 (class 0 OID 0)
-- Dependencies: 256
-- Name: COLUMN team_format_mappings.league_id; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.team_format_mappings.league_id IS 'League identifier (CNSWPL, NSTF, APTA_CHICAGO, CITA)';


--
-- TOC entry 4209 (class 0 OID 0)
-- Dependencies: 256
-- Name: COLUMN team_format_mappings.user_input_format; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.team_format_mappings.user_input_format IS 'Format that users might enter or have in their session data';


--
-- TOC entry 4210 (class 0 OID 0)
-- Dependencies: 256
-- Name: COLUMN team_format_mappings.database_series_format; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.team_format_mappings.database_series_format IS 'Actual series format as stored in the database';


--
-- TOC entry 4211 (class 0 OID 0)
-- Dependencies: 256
-- Name: COLUMN team_format_mappings.mapping_type; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.team_format_mappings.mapping_type IS 'Type of mapping (series_mapping, team_mapping, etc.)';


--
-- TOC entry 4212 (class 0 OID 0)
-- Dependencies: 256
-- Name: COLUMN team_format_mappings.description; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.team_format_mappings.description IS 'Human-readable description of this mapping';


--
-- TOC entry 257 (class 1259 OID 46610)
-- Name: team_format_mappings_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.team_format_mappings_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- TOC entry 4213 (class 0 OID 0)
-- Dependencies: 257
-- Name: team_format_mappings_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.team_format_mappings_id_seq OWNED BY public.team_format_mappings.id;


--
-- TOC entry 258 (class 1259 OID 46611)
-- Name: teams; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.teams (
    id integer NOT NULL,
    club_id integer NOT NULL,
    series_id integer NOT NULL,
    league_id integer NOT NULL,
    team_name character varying(255) NOT NULL,
    external_team_id character varying(255),
    is_active boolean DEFAULT true,
    created_at timestamp with time zone DEFAULT CURRENT_TIMESTAMP,
    updated_at timestamp with time zone DEFAULT CURRENT_TIMESTAMP,
    team_alias character varying(255)
);


--
-- TOC entry 259 (class 1259 OID 46619)
-- Name: teams_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.teams_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- TOC entry 4214 (class 0 OID 0)
-- Dependencies: 259
-- Name: teams_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.teams_id_seq OWNED BY public.teams.id;


--
-- TOC entry 260 (class 1259 OID 46620)
-- Name: user_activity_logs; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.user_activity_logs (
    id integer NOT NULL,
    user_email character varying(255) NOT NULL,
    activity_type character varying(255) NOT NULL,
    page character varying(255),
    action text,
    details text,
    ip_address character varying(45),
    "timestamp" timestamp with time zone DEFAULT CURRENT_TIMESTAMP
);


--
-- TOC entry 261 (class 1259 OID 46626)
-- Name: user_activity_logs_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.user_activity_logs_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- TOC entry 4215 (class 0 OID 0)
-- Dependencies: 261
-- Name: user_activity_logs_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.user_activity_logs_id_seq OWNED BY public.user_activity_logs.id;


--
-- TOC entry 262 (class 1259 OID 46627)
-- Name: user_instructions; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.user_instructions (
    id integer NOT NULL,
    user_email character varying(255) NOT NULL,
    instruction text NOT NULL,
    series_id integer,
    team_id integer,
    created_at timestamp with time zone DEFAULT CURRENT_TIMESTAMP,
    is_active boolean DEFAULT true
);


--
-- TOC entry 263 (class 1259 OID 46634)
-- Name: user_instructions_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.user_instructions_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- TOC entry 4216 (class 0 OID 0)
-- Dependencies: 263
-- Name: user_instructions_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.user_instructions_id_seq OWNED BY public.user_instructions.id;


--
-- TOC entry 264 (class 1259 OID 46635)
-- Name: users_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.users_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- TOC entry 4217 (class 0 OID 0)
-- Dependencies: 264
-- Name: users_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.users_id_seq OWNED BY public.players.id;


--
-- TOC entry 265 (class 1259 OID 46636)
-- Name: users_id_seq1; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.users_id_seq1
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- TOC entry 4218 (class 0 OID 0)
-- Dependencies: 265
-- Name: users_id_seq1; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.users_id_seq1 OWNED BY public.users.id;


--
-- TOC entry 3779 (class 2604 OID 46637)
-- Name: club_leagues id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.club_leagues ALTER COLUMN id SET DEFAULT nextval('public.club_leagues_id_seq'::regclass);


--
-- TOC entry 3781 (class 2604 OID 46638)
-- Name: clubs id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.clubs ALTER COLUMN id SET DEFAULT nextval('public.clubs_id_seq'::regclass);


--
-- TOC entry 3783 (class 2604 OID 46639)
-- Name: leagues id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.leagues ALTER COLUMN id SET DEFAULT nextval('public.leagues_id_seq'::regclass);


--
-- TOC entry 3786 (class 2604 OID 46640)
-- Name: match_scores id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.match_scores ALTER COLUMN id SET DEFAULT nextval('public.match_scores_id_seq'::regclass);


--
-- TOC entry 3804 (class 2604 OID 46641)
-- Name: player_availability id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.player_availability ALTER COLUMN id SET DEFAULT nextval('public.player_availability_id_seq'::regclass);


--
-- TOC entry 3807 (class 2604 OID 46642)
-- Name: player_history id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.player_history ALTER COLUMN id SET DEFAULT nextval('public.player_history_id_seq'::regclass);


--
-- TOC entry 3809 (class 2604 OID 46643)
-- Name: player_season_tracking id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.player_season_tracking ALTER COLUMN id SET DEFAULT nextval('public.player_season_tracking_id_seq'::regclass);


--
-- TOC entry 3788 (class 2604 OID 46644)
-- Name: players id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.players ALTER COLUMN id SET DEFAULT nextval('public.users_id_seq'::regclass);


--
-- TOC entry 3815 (class 2604 OID 46645)
-- Name: poll_choices id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.poll_choices ALTER COLUMN id SET DEFAULT nextval('public.poll_choices_id_seq'::regclass);


--
-- TOC entry 3816 (class 2604 OID 46646)
-- Name: poll_responses id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.poll_responses ALTER COLUMN id SET DEFAULT nextval('public.poll_responses_id_seq'::regclass);


--
-- TOC entry 3818 (class 2604 OID 46647)
-- Name: polls id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.polls ALTER COLUMN id SET DEFAULT nextval('public.polls_id_seq'::regclass);


--
-- TOC entry 3820 (class 2604 OID 46648)
-- Name: pro_lessons id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.pro_lessons ALTER COLUMN id SET DEFAULT nextval('public.pro_lessons_id_seq'::regclass);


--
-- TOC entry 3824 (class 2604 OID 46649)
-- Name: pros id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.pros ALTER COLUMN id SET DEFAULT nextval('public.pros_id_seq'::regclass);


--
-- TOC entry 3828 (class 2604 OID 46650)
-- Name: schedule id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.schedule ALTER COLUMN id SET DEFAULT nextval('public.schedule_id_seq'::regclass);


--
-- TOC entry 3830 (class 2604 OID 46651)
-- Name: series id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.series ALTER COLUMN id SET DEFAULT nextval('public.series_id_seq'::regclass);


--
-- TOC entry 3832 (class 2604 OID 46652)
-- Name: series_leagues id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.series_leagues ALTER COLUMN id SET DEFAULT nextval('public.series_leagues_id_seq'::regclass);


--
-- TOC entry 3834 (class 2604 OID 46653)
-- Name: series_name_mappings id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.series_name_mappings ALTER COLUMN id SET DEFAULT nextval('public.series_name_mappings_id_seq'::regclass);


--
-- TOC entry 3837 (class 2604 OID 46654)
-- Name: series_stats id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.series_stats ALTER COLUMN id SET DEFAULT nextval('public.series_stats_id_seq'::regclass);


--
-- TOC entry 3839 (class 2604 OID 46655)
-- Name: team_format_mappings id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.team_format_mappings ALTER COLUMN id SET DEFAULT nextval('public.team_format_mappings_id_seq'::regclass);


--
-- TOC entry 3844 (class 2604 OID 46656)
-- Name: teams id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.teams ALTER COLUMN id SET DEFAULT nextval('public.teams_id_seq'::regclass);


--
-- TOC entry 3848 (class 2604 OID 46657)
-- Name: user_activity_logs id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.user_activity_logs ALTER COLUMN id SET DEFAULT nextval('public.user_activity_logs_id_seq'::regclass);


--
-- TOC entry 3850 (class 2604 OID 46658)
-- Name: user_instructions id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.user_instructions ALTER COLUMN id SET DEFAULT nextval('public.user_instructions_id_seq'::regclass);


--
-- TOC entry 3801 (class 2604 OID 46659)
-- Name: users id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.users ALTER COLUMN id SET DEFAULT nextval('public.users_id_seq1'::regclass);


--
-- TOC entry 4131 (class 0 OID 46443)
-- Dependencies: 216
-- Data for Name: activity_log; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.activity_log (id, player_id, team_id, user_id, action_type, action_description, related_id, related_type, ip_address, user_agent, extra_data, "timestamp") FROM stdin;
1205edd9-d0a4-407e-8fa5-0863f8ff66f2	165592	\N	43	team_email	Team email was sent	\N	\N	192.168.1.213	Mozilla/5.0 (iPad; CPU OS 15_0 like Mac OS X)	\N	2025-06-20 11:37:32.520341-05
fd2c378d-e997-4898-b17f-6ecddec4caa4	165597	2914	72	score_submitted	Match score was submitted	4133	match	192.168.1.90	Mozilla/5.0 (iPad; CPU OS 15_0 like Mac OS X)	\N	2025-06-20 09:44:45.520341-05
4bd8fc07-69fc-4342-8ff2-676f450e1587	\N	2910	74	team_email	Team email was sent	\N	\N	192.168.1.106	Mozilla/5.0 (iPad; CPU OS 15_0 like Mac OS X)	\N	2025-06-20 13:33:23.520341-05
d95f1932-7507-4393-9805-b4610551dfeb	\N	2910	73	score_submitted	Match score was submitted	8139	match	192.168.1.230	Mozilla/5.0 (iPad; CPU OS 15_0 like Mac OS X)	\N	2025-06-20 17:48:13.520341-05
557bb66d-a9fd-407b-9033-25d918dd7f30	165585	2912	74	page_visit	Visited schedule page	\N	\N	192.168.1.238	Mozilla/5.0 (iPad; CPU OS 15_0 like Mac OS X)	{"page": "lineup", "duration": 201}	2025-06-20 12:24:42.520341-05
9a7df7b1-0546-4411-a968-5d001c11e687	\N	2911	74	logout	User logged out of Rally app	\N	\N	192.168.1.70	Mozilla/5.0 (Windows NT 10.0; Win64; x64)	\N	2025-06-20 16:37:37.520341-05
d7159dc2-8e31-4a64-805e-5e691ec3879f	165593	2910	50	login	User Adam Seyb logged in	\N	\N	192.168.1.117	Mozilla/5.0 (iPhone; CPU iPhone OS 15_0 like Mac OS X)	\N	2025-06-20 19:36:34.520341-05
f3c054d0-928a-4cc6-aa62-e7fdb2203f82	\N	\N	52	admin_action	Admin performed system backup	\N	\N	192.168.1.55	Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)	\N	2025-06-20 18:43:11.520341-05
d0640175-b374-4db2-a29c-f54920a3ec6d	\N	\N	50	data_update	Data was updated in system	\N	\N	192.168.1.192	Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)	\N	2025-06-20 09:03:05.520341-05
d4810c8f-2550-4b40-ba21-02178f5bf0e4	165581	\N	52	availability_update	Debbie Goldstein marked as available	\N	\N	192.168.1.235	Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)	\N	2025-06-20 17:35:49.520341-05
6ddee979-8171-4921-9ec3-21bfea017eac	165591	2917	49	lineup_update	Team lineup was updated	\N	\N	192.168.1.245	Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)	\N	2025-06-20 19:41:33.520341-05
e8ee2a0e-6760-4275-837d-cb142c0740c7	165581	\N	70	admin_action	Admin performed system backup	\N	\N	192.168.1.193	Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)	\N	2025-06-20 21:59:22.520341-05
55e35c8a-de25-497d-8004-40ca9655e860	165588	2912	74	availability_update	Jody Rotblatt marked as unavailable	\N	\N	192.168.1.47	Mozilla/5.0 (iPhone; CPU iPhone OS 15_0 like Mac OS X)	\N	2025-06-20 09:40:24.520341-05
9bf9c99c-0dd8-4e51-839e-66f60169a6b6	165586	2913	70	login	User Dave Israel logged in	\N	\N	192.168.1.31	Mozilla/5.0 (iPad; CPU OS 15_0 like Mac OS X)	\N	2025-06-20 17:43:52.520341-05
47fae3a1-4c4c-47dd-9c46-6f217bdec7db	165592	\N	52	lineup_update	Team lineup was updated	\N	\N	192.168.1.129	Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)	\N	2025-06-20 10:31:18.520341-05
ec6722ce-f928-447f-966f-e95745fcb0f1	165579	\N	73	match_created	Match result created for team	5832	match	192.168.1.189	Mozilla/5.0 (Windows NT 10.0; Win64; x64)	{"home_score": 3, "away_score": 4}	2025-06-20 08:23:30.520341-05
32b3b0d7-00ed-4d01-970c-05819a62de6d	\N	2911	70	lineup_update	Team lineup was updated	\N	\N	192.168.1.175	Mozilla/5.0 (iPad; CPU OS 15_0 like Mac OS X)	\N	2025-06-20 15:21:54.520341-05
5692a375-c61f-4fa0-b2b8-8a5c0fd11a28	\N	2914	51	score_submitted	Match score was submitted	4997	match	192.168.1.225	Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)	\N	2025-06-19 13:27:30.610326-05
e4bfe85b-3240-4299-ac8b-a6ee2019ced9	165578	2915	43	data_update	Data was updated in system	\N	\N	192.168.1.132	Mozilla/5.0 (iPhone; CPU iPhone OS 15_0 like Mac OS X)	\N	2025-06-19 21:02:11.610326-05
1f84bc80-d7f6-4e69-8d1e-ca7d3c5100d9	165596	2913	43	lineup_update	Team lineup was updated	\N	\N	192.168.1.60	Mozilla/5.0 (iPhone; CPU iPhone OS 15_0 like Mac OS X)	\N	2025-06-19 08:22:01.610326-05
c3297ac1-91db-4ca9-85a3-a671830ad668	165583	\N	43	admin_action	Admin performed system backup	\N	\N	192.168.1.195	Mozilla/5.0 (iPad; CPU OS 15_0 like Mac OS X)	\N	2025-06-19 19:24:01.610326-05
708e3a0c-8f1e-4ab1-b2c8-87d60dac52a9	165579	\N	50	login	User Adam Seyb logged in	\N	\N	192.168.1.74	Mozilla/5.0 (iPhone; CPU iPhone OS 15_0 like Mac OS X)	\N	2025-06-18 19:33:14.628359-05
01d73db8-6d3b-4dbc-9a4b-ee6732ce36ff	\N	2914	73	score_submitted	Match score was submitted	2580	match	192.168.1.78	Mozilla/5.0 (iPhone; CPU iPhone OS 15_0 like Mac OS X)	\N	2025-06-18 19:59:41.628359-05
5c72bda5-7ec6-45ef-9087-04354f47f588	165584	2914	70	poll_response	Alison Morgan responded to team poll	670	poll	192.168.1.117	Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)	\N	2025-06-18 21:04:37.628359-05
b0e5f468-bd76-4c6f-bbe1-54a10e0406c2	\N	\N	50	data_update	Data was updated in system	\N	\N	192.168.1.175	Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)	\N	2025-06-18 22:35:12.628359-05
b74e9738-f425-44be-8db5-ee65893d275b	165591	2912	74	login	User Brian Stutland logged in	\N	\N	192.168.1.14	Mozilla/5.0 (iPad; CPU OS 15_0 like Mac OS X)	\N	2025-06-18 17:13:02.628359-05
075fc872-a38d-4995-9f6a-980ce54745ec	165582	2915	49	team_email	Team email was sent	\N	\N	192.168.1.240	Mozilla/5.0 (iPad; CPU OS 15_0 like Mac OS X)	\N	2025-06-18 14:20:10.628359-05
ad9842cc-94ff-45d2-bfad-0550822034da	\N	\N	72	poll_response	Team poll response received	218	poll	192.168.1.122	Mozilla/5.0 (iPad; CPU OS 15_0 like Mac OS X)	\N	2025-06-18 10:22:54.628359-05
ad8cda26-d65d-4bbf-a62e-38624105232b	165587	2911	72	score_submitted	Match score was submitted	4561	match	192.168.1.61	Mozilla/5.0 (iPad; CPU OS 15_0 like Mac OS X)	\N	2025-06-18 12:18:20.628359-05
02a4e7ca-4124-4fb6-8b63-a0da09ab04e3	165582	\N	51	admin_action	Admin performed data import	\N	\N	192.168.1.4	Mozilla/5.0 (iPhone; CPU iPhone OS 15_0 like Mac OS X)	\N	2025-06-18 18:14:43.628359-05
7e3ee896-1295-4898-ad66-b84b7ee570d6	165583	\N	74	logout	User logged out of Rally app	\N	\N	192.168.1.247	Mozilla/5.0 (Windows NT 10.0; Win64; x64)	\N	2025-06-18 20:39:09.628359-05
64927bf6-a8d2-4c42-838d-78257602f746	165597	2908	50	logout	User logged out of Rally app	\N	\N	192.168.1.121	Mozilla/5.0 (iPhone; CPU iPhone OS 15_0 like Mac OS X)	\N	2025-06-18 14:57:41.628359-05
52d5cedb-99e5-4921-a499-a4c2239222ae	165594	\N	49	match_created	Match result created for team	5350	match	192.168.1.170	Mozilla/5.0 (iPad; CPU OS 15_0 like Mac OS X)	{"home_score": 3, "away_score": 3}	2025-06-18 10:53:00.628359-05
055811b1-b06b-4736-ab60-02f38e747b27	165585	\N	50	logout	User logged out of Rally app	\N	\N	192.168.1.20	Mozilla/5.0 (iPhone; CPU iPhone OS 15_0 like Mac OS X)	\N	2025-06-18 17:28:27.628359-05
b2409011-435e-4099-a15b-5b499d3ac295	165589	2911	72	poll_response	Svetlana Schroeder responded to team poll	495	poll	192.168.1.120	Mozilla/5.0 (Windows NT 10.0; Win64; x64)	\N	2025-06-18 10:18:28.628359-05
70d5234c-9cd8-4964-a87e-89f553a9e062	165585	\N	52	dashboard_access	Admin accessed activity dashboard	\N	\N	192.168.1.87	Mozilla/5.0 (Windows NT 10.0; Win64; x64)	\N	2025-06-18 13:24:52.628359-05
7c431e49-209c-4477-9285-4d876558e397	165595	2911	51	admin_action	Admin performed league update	\N	\N	192.168.1.216	Mozilla/5.0 (iPhone; CPU iPhone OS 15_0 like Mac OS X)	\N	2025-06-18 13:43:24.628359-05
35c9c3ca-f4bf-4952-b91e-dbda40d78b5f	165593	2915	52	admin_action	Admin performed data import	\N	\N	192.168.1.250	Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)	\N	2025-06-18 08:43:23.628359-05
9243ad04-4cc7-4424-85f9-16cbabe9089b	165586	2916	70	dashboard_access	Admin accessed activity dashboard	\N	\N	192.168.1.252	Mozilla/5.0 (Windows NT 10.0; Win64; x64)	\N	2025-06-18 09:43:41.628359-05
04db426b-7a00-4c5f-b4d3-23870d822ee8	\N	2917	43	admin_action	Admin performed system backup	\N	\N	192.168.1.35	Mozilla/5.0 (iPad; CPU OS 15_0 like Mac OS X)	\N	2025-06-18 20:33:45.628359-05
5e46aadb-17c0-45c2-b6a1-edc3ef1c97c6	165586	\N	50	lineup_update	Team lineup was updated	\N	\N	192.168.1.82	Mozilla/5.0 (Windows NT 10.0; Win64; x64)	\N	2025-06-18 14:22:02.628359-05
1e6085db-52ed-4612-9ba6-97b799bcbea7	165593	2915	72	lineup_update	Team lineup was updated	\N	\N	192.168.1.242	Mozilla/5.0 (Windows NT 10.0; Win64; x64)	\N	2025-06-18 12:58:05.628359-05
9c18af77-59a2-4c5e-93c7-240742df145e	165590	\N	51	team_email	Team email was sent	\N	\N	192.168.1.165	Mozilla/5.0 (Windows NT 10.0; Win64; x64)	\N	2025-06-17 12:31:07.701963-05
386462ab-2eea-4921-bd1c-f076a86042ce	\N	2915	52	data_update	Data was updated in system	\N	\N	192.168.1.189	Mozilla/5.0 (Windows NT 10.0; Win64; x64)	\N	2025-06-17 12:10:12.701963-05
baf61e88-fb28-474c-a28a-692dc55b4b61	165581	\N	70	dashboard_access	Admin accessed activity dashboard	\N	\N	192.168.1.190	Mozilla/5.0 (iPhone; CPU iPhone OS 15_0 like Mac OS X)	\N	2025-06-17 20:15:33.701963-05
9aa4fafa-5c02-4fcc-8c89-e411294a582b	165592	2909	72	data_update	Data was updated in system	\N	\N	192.168.1.102	Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)	\N	2025-06-17 15:38:08.701963-05
c0ed0f6a-af6a-4a48-b083-b4fb3ff4bd80	165586	\N	74	logout	User logged out of Rally app	\N	\N	192.168.1.79	Mozilla/5.0 (Windows NT 10.0; Win64; x64)	\N	2025-06-16 14:58:25.719767-05
19ce2f2c-30ab-45c8-835c-aef69cd00218	\N	\N	43	score_submitted	Match score was submitted	7825	match	192.168.1.192	Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)	\N	2025-06-16 12:55:08.719767-05
ba684b35-2339-4e95-a752-c670680fff76	165581	\N	72	page_visit	Visited schedule page	\N	\N	192.168.1.126	Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)	{"page": "availability", "duration": 54}	2025-06-16 09:14:06.719767-05
22e523b3-ebd0-405e-92f5-70787e88d848	165588	2908	49	team_email	Team email was sent	\N	\N	192.168.1.95	Mozilla/5.0 (iPhone; CPU iPhone OS 15_0 like Mac OS X)	\N	2025-06-16 19:14:48.719767-05
9e129c37-d106-4a1e-a8af-10a77c106fbf	\N	\N	50	poll_response	Team poll response received	546	poll	192.168.1.140	Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)	\N	2025-06-16 15:07:54.719767-05
2d31cb1e-4b7b-448e-b2d6-60346b3fd9fb	\N	\N	49	dashboard_access	Admin accessed activity dashboard	\N	\N	192.168.1.15	Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)	\N	2025-06-16 21:23:30.719767-05
d29dfb9c-1f97-47d6-ab22-03f2b7b8ed10	\N	2917	49	dashboard_access	Admin accessed activity dashboard	\N	\N	192.168.1.211	Mozilla/5.0 (iPad; CPU OS 15_0 like Mac OS X)	\N	2025-06-16 11:32:18.719767-05
bea56125-55c2-4baa-9229-e74e0376deea	165586	\N	70	poll_response	Elizabeth Fox responded to team poll	983	poll	192.168.1.118	Mozilla/5.0 (iPad; CPU OS 15_0 like Mac OS X)	\N	2025-06-15 16:11:51.743374-05
756af952-cb7d-4d3a-bf38-2bce6b664255	165582	2916	49	data_update	Data was updated in system	\N	\N	192.168.1.255	Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)	\N	2025-06-15 14:46:56.743374-05
7f53284f-3e00-4da6-9698-4d8296337465	165589	2916	49	page_visit	Visited availability page	\N	\N	192.168.1.43	Mozilla/5.0 (iPad; CPU OS 15_0 like Mac OS X)	{"page": "schedule", "duration": 183}	2025-06-15 21:13:54.743374-05
7ef42051-cf5b-47c7-a9ae-e93fe7789b1e	\N	\N	74	data_update	Data was updated in system	\N	\N	192.168.1.122	Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)	\N	2025-06-15 18:27:34.743374-05
824e2239-a153-4072-8fe5-d05f13f0420d	\N	2909	51	login	User Stephen Statkus logged in	\N	\N	192.168.1.98	Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)	\N	2025-06-15 15:49:30.743374-05
f844f951-e138-4018-bdd4-050902e9269b	165592	\N	43	poll_response	Kristen Evans responded to team poll	112	poll	192.168.1.17	Mozilla/5.0 (iPad; CPU OS 15_0 like Mac OS X)	\N	2025-06-15 09:50:21.743374-05
8bad4be5-94cc-4900-8e68-57c9e2ea4935	165593	2915	50	login	User Adam Seyb logged in	\N	\N	192.168.1.69	Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)	\N	2025-06-15 18:49:05.743374-05
9119fea5-3b4b-4402-a5da-21a672aa99b8	165587	2912	73	match_created	Match result created for Biltmore CC - 19	1372	match	192.168.1.243	Mozilla/5.0 (Windows NT 10.0; Win64; x64)	{"home_score": 1, "away_score": 2}	2025-06-15 08:25:07.743374-05
6c2eb4a0-01b5-47aa-bff5-196201c5fd09	165587	\N	52	page_visit	Visited schedule page	\N	\N	192.168.1.101	Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)	{"page": "schedule", "duration": 273}	2025-06-15 20:37:11.743374-05
bf2be04e-83ad-4255-9266-a836755424b0	165597	\N	70	page_visit	Visited improve page	\N	\N	192.168.1.36	Mozilla/5.0 (iPhone; CPU iPhone OS 15_0 like Mac OS X)	{"page": "lineup", "duration": 282}	2025-06-15 13:28:53.743374-05
2fe4e963-038b-49e1-a9e0-a5f3ebebd22a	165593	\N	50	logout	User logged out of Rally app	\N	\N	192.168.1.36	Mozilla/5.0 (iPhone; CPU iPhone OS 15_0 like Mac OS X)	\N	2025-06-15 17:33:11.743374-05
b02e9ec0-b378-44ec-be1d-6f3970b5e403	\N	\N	43	poll_response	Team poll response received	304	poll	192.168.1.84	Mozilla/5.0 (iPad; CPU OS 15_0 like Mac OS X)	\N	2025-06-15 16:02:26.743374-05
f639041f-61fa-423d-a0f0-0c45d53c655c	\N	2908	49	logout	User logged out of Rally app	\N	\N	192.168.1.11	Mozilla/5.0 (iPhone; CPU iPhone OS 15_0 like Mac OS X)	\N	2025-06-15 18:01:46.743374-05
7bd5b259-7dda-4aed-ba99-335b3b814014	165585	\N	51	poll_response	Jamie Zaransky responded to team poll	167	poll	192.168.1.243	Mozilla/5.0 (iPad; CPU OS 15_0 like Mac OS X)	\N	2025-06-15 17:30:50.743374-05
b4af66f9-6cb5-4b11-b1c3-aad0294678b4	165578	2912	52	match_created	Match result created for Biltmore CC - 19	2153	match	192.168.1.204	Mozilla/5.0 (iPad; CPU OS 15_0 like Mac OS X)	{"home_score": 5, "away_score": 1}	2025-06-15 22:10:08.743374-05
89425f30-16ec-4095-96d6-307676116de5	165591	2916	51	lineup_update	Team lineup was updated	\N	\N	192.168.1.65	Mozilla/5.0 (iPhone; CPU iPhone OS 15_0 like Mac OS X)	\N	2025-06-15 08:57:35.743374-05
84500a82-e84e-4b61-977d-e1948a3a28f1	165591	2914	52	team_email	Team email was sent	\N	\N	192.168.1.112	Mozilla/5.0 (iPhone; CPU iPhone OS 15_0 like Mac OS X)	\N	2025-06-15 18:37:38.743374-05
8669bcae-626e-4866-a08d-705dcfa89278	165589	\N	70	admin_action	Admin performed system backup	\N	\N	192.168.1.60	Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)	\N	2025-06-15 22:51:36.743374-05
3cc7bc3e-7326-4d06-b524-aa9aa4a7a83c	\N	\N	74	dashboard_access	Admin accessed activity dashboard	\N	\N	192.168.1.125	Mozilla/5.0 (iPhone; CPU iPhone OS 15_0 like Mac OS X)	\N	2025-06-15 08:24:33.743374-05
93c32521-f08c-40da-8685-aa8f814fae8a	165580	\N	74	score_submitted	Match score was submitted	6852	match	192.168.1.206	Mozilla/5.0 (Windows NT 10.0; Win64; x64)	\N	2025-06-15 18:49:13.743374-05
aad8b1d9-36c7-45aa-b700-71f962b0522c	\N	\N	74	poll_response	Team poll response received	879	poll	192.168.1.95	Mozilla/5.0 (Windows NT 10.0; Win64; x64)	\N	2025-06-14 16:49:51.803264-05
8ab44e39-a97c-44c9-92d8-2beefa3d89c1	165597	\N	50	logout	User logged out of Rally app	\N	\N	192.168.1.144	Mozilla/5.0 (iPad; CPU OS 15_0 like Mac OS X)	\N	2025-06-14 13:50:22.803264-05
a41b9d8d-cb3b-423e-9c8f-1f7c05c4bf8d	\N	\N	70	logout	User logged out of Rally app	\N	\N	192.168.1.247	Mozilla/5.0 (iPhone; CPU iPhone OS 15_0 like Mac OS X)	\N	2025-06-14 20:34:16.803264-05
f0ba780d-f7ce-4896-9e64-339910c227b9	165591	\N	43	dashboard_access	Admin accessed activity dashboard	\N	\N	192.168.1.27	Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)	\N	2025-06-14 19:27:47.803264-05
f4aa30a4-e034-4dfe-adda-6d056c38201a	165586	\N	52	poll_response	Elizabeth Fox responded to team poll	879	poll	192.168.1.134	Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)	\N	2025-06-14 13:13:24.803264-05
4cb89086-eb2b-433c-85e4-ac8373273215	\N	2913	52	admin_action	Admin performed league update	\N	\N	192.168.1.154	Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)	\N	2025-06-14 08:58:53.803264-05
f242ae48-bedc-4e3f-beee-9950ad4489bb	\N	\N	43	logout	User logged out of Rally app	\N	\N	192.168.1.72	Mozilla/5.0 (iPad; CPU OS 15_0 like Mac OS X)	\N	2025-06-14 10:24:11.803264-05
b422e476-7769-439c-a013-dba90323f8f9	165582	2917	50	poll_response	Leslie Katz responded to team poll	441	poll	192.168.1.70	Mozilla/5.0 (iPhone; CPU iPhone OS 15_0 like Mac OS X)	\N	2025-06-14 13:50:50.803264-05
0fb7f641-385e-4d77-af71-6a1350c72c2b	165580	\N	50	score_submitted	Match score was submitted	1458	match	192.168.1.23	Mozilla/5.0 (Windows NT 10.0; Win64; x64)	\N	2025-06-14 16:03:20.803264-05
dd0c357d-c000-48d5-b731-daebf0584b98	\N	\N	51	logout	User logged out of Rally app	\N	\N	192.168.1.82	Mozilla/5.0 (iPad; CPU OS 15_0 like Mac OS X)	\N	2025-06-14 13:12:22.803264-05
f293b7bb-ef2e-4805-bab1-e9a3cdee40b3	165581	\N	51	admin_action	Admin performed user management	\N	\N	192.168.1.58	Mozilla/5.0 (Windows NT 10.0; Win64; x64)	\N	2025-06-14 11:57:07.803264-05
8b153936-73fd-44a8-9ca1-7743fc4b1bcc	165586	\N	70	login	User Dave Israel logged in	\N	\N	192.168.1.114	Mozilla/5.0 (Windows NT 10.0; Win64; x64)	\N	2025-06-14 10:28:01.803264-05
20e93a6c-59e6-4196-9d91-8d807662ad02	165585	2911	70	data_update	Data was updated in system	\N	\N	192.168.1.111	Mozilla/5.0 (iPhone; CPU iPhone OS 15_0 like Mac OS X)	\N	2025-06-14 18:14:02.803264-05
daea279b-c744-4604-b267-47fa29d31a9a	165582	2913	52	match_created	Match result created for Biltmore CC - 21	5910	match	192.168.1.117	Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)	{"home_score": 1, "away_score": 5}	2025-06-14 16:53:14.803264-05
d6bd83b2-a4bc-4a90-a3e9-bf89b4b3c1d1	165594	\N	43	team_email	Team email was sent	\N	\N	192.168.1.75	Mozilla/5.0 (iPhone; CPU iPhone OS 15_0 like Mac OS X)	\N	2025-06-14 09:22:51.803264-05
e0470ae5-3c45-4b9a-b1fb-012875564960	165579	\N	70	availability_update	Lisa Korach marked as available	\N	\N	192.168.1.82	Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)	\N	2025-06-14 15:20:00.803264-05
56894ef2-f951-4072-98be-2267ad289dd5	165579	2912	70	match_created	Match result created for Biltmore CC - 19	9756	match	192.168.1.183	Mozilla/5.0 (iPhone; CPU iPhone OS 15_0 like Mac OS X)	{"home_score": 6, "away_score": 2}	2025-06-13 08:43:17.844379-05
a5239698-fc7d-4689-a989-b4cfc4ae3cda	\N	2910	51	lineup_update	Team lineup was updated	\N	\N	192.168.1.38	Mozilla/5.0 (iPhone; CPU iPhone OS 15_0 like Mac OS X)	\N	2025-06-13 08:48:53.844379-05
59da9cbd-8acd-4d25-9796-f8f83bdaacac	\N	2913	70	admin_action	Admin performed user management	\N	\N	192.168.1.235	Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)	\N	2025-06-13 18:12:59.844379-05
58ee0725-3214-48bb-80a0-24a6ed29666e	\N	2912	73	data_update	Data was updated in system	\N	\N	192.168.1.245	Mozilla/5.0 (iPad; CPU OS 15_0 like Mac OS X)	\N	2025-06-13 08:25:09.844379-05
4bbcc778-58f5-4e64-99b5-274f5ecd5697	165591	\N	49	score_submitted	Match score was submitted	2506	match	192.168.1.220	Mozilla/5.0 (iPhone; CPU iPhone OS 15_0 like Mac OS X)	\N	2025-06-13 13:22:31.844379-05
ed6df34d-d2bd-4f64-ab78-981937a128b4	165596	2913	51	poll_response	Maggie Jessopp responded to team poll	278	poll	192.168.1.24	Mozilla/5.0 (iPad; CPU OS 15_0 like Mac OS X)	\N	2025-06-13 08:30:27.844379-05
719ef454-cbb0-480f-aad5-fa9e819430a0	\N	2915	51	admin_action	Admin performed data import	\N	\N	192.168.1.7	Mozilla/5.0 (Windows NT 10.0; Win64; x64)	\N	2025-06-13 13:14:42.844379-05
f068f6d8-a141-42c6-b04c-a1399b29bea8	165593	\N	51	page_visit	Visited schedule page	\N	\N	192.168.1.66	Mozilla/5.0 (Windows NT 10.0; Win64; x64)	{"page": "availability", "duration": 166}	2025-06-13 14:31:32.844379-05
49df6597-15a4-4359-94e6-01b30eb672a8	165586	\N	50	login	User Adam Seyb logged in	\N	\N	192.168.1.172	Mozilla/5.0 (iPad; CPU OS 15_0 like Mac OS X)	\N	2025-06-13 08:19:39.844379-05
6cd916ef-2ee0-4e1e-b837-e6808fb98495	\N	\N	74	poll_response	Team poll response received	231	poll	192.168.1.82	Mozilla/5.0 (iPhone; CPU iPhone OS 15_0 like Mac OS X)	\N	2025-06-13 13:38:01.844379-05
847440ba-430c-4352-a730-a14f2b78b534	\N	\N	74	availability_update	Availability updated to available	\N	\N	192.168.1.130	Mozilla/5.0 (Windows NT 10.0; Win64; x64)	\N	2025-06-12 10:11:33.870359-05
4fc7276e-57e8-4c39-aa69-1f0ec5c83ac0	\N	\N	52	page_visit	Visited matches page	\N	\N	192.168.1.217	Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)	{"page": "lineup", "duration": 81}	2025-06-12 19:12:03.870359-05
f39f8309-b289-46d7-9c6e-9689f697b98e	165595	\N	50	lineup_update	Team lineup was updated	\N	\N	192.168.1.80	Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)	\N	2025-06-11 09:26:09.875559-05
1287548a-967e-45f8-b6d2-037c5762295d	165595	\N	74	login	User Brian Stutland logged in	\N	\N	192.168.1.11	Mozilla/5.0 (iPhone; CPU iPhone OS 15_0 like Mac OS X)	\N	2025-06-11 22:00:45.875559-05
f8624e3c-3ed0-4556-8045-2e05240ecee9	\N	2911	70	score_submitted	Match score was submitted	1777	match	192.168.1.141	Mozilla/5.0 (iPhone; CPU iPhone OS 15_0 like Mac OS X)	\N	2025-06-11 15:33:47.875559-05
f05fd154-50a3-42bc-a462-fe7d6eab1270	165584	\N	72	dashboard_access	Admin accessed activity dashboard	\N	\N	192.168.1.133	Mozilla/5.0 (iPhone; CPU iPhone OS 15_0 like Mac OS X)	\N	2025-06-11 08:52:50.875559-05
c67e5ded-dc89-44e9-919f-a7293189c35d	165581	\N	49	page_visit	Visited improve page	\N	\N	192.168.1.150	Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)	{"page": "availability", "duration": 185}	2025-06-11 13:08:23.875559-05
4ab42675-9ea7-4abe-9ae5-85af59fe9ff2	165580	\N	73	logout	User logged out of Rally app	\N	\N	192.168.1.248	Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)	\N	2025-06-11 09:50:05.875559-05
c94191ae-6434-4e3d-b44f-00f243f30558	\N	\N	73	availability_update	Availability updated to maybe	\N	\N	192.168.1.211	Mozilla/5.0 (iPad; CPU OS 15_0 like Mac OS X)	\N	2025-06-11 19:29:55.875559-05
3ab0ad3d-37cf-4264-ac64-8ada447f9c0d	165594	2916	72	login	User Scott Osterman logged in	\N	\N	192.168.1.120	Mozilla/5.0 (iPhone; CPU iPhone OS 15_0 like Mac OS X)	\N	2025-06-11 18:52:59.875559-05
5758d781-6020-4bc4-8abb-b976218145d7	165583	2916	70	score_submitted	Match score was submitted	6945	match	192.168.1.69	Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)	\N	2025-06-11 09:37:41.875559-05
6dbdaecb-3ff1-4a9c-b18b-25bea17ab310	165590	2909	73	login	User Allen Guon logged in	\N	\N	192.168.1.6	Mozilla/5.0 (Windows NT 10.0; Win64; x64)	\N	2025-06-11 14:31:51.875559-05
a598d765-64de-4748-a596-fb9895768df0	165588	2915	49	admin_action	Admin performed data import	\N	\N	192.168.1.8	Mozilla/5.0 (iPhone; CPU iPhone OS 15_0 like Mac OS X)	\N	2025-06-10 14:24:06.901829-05
b18dbe58-03c2-43d1-81e3-2ff6467654ec	165587	2912	49	login	User Victor Forman logged in	\N	\N	192.168.1.173	Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)	\N	2025-06-10 15:41:08.901829-05
78b2eb0d-4380-4635-983c-478bf8b6a95e	\N	2910	49	login	User Victor Forman logged in	\N	\N	192.168.1.87	Mozilla/5.0 (iPhone; CPU iPhone OS 15_0 like Mac OS X)	\N	2025-06-10 18:17:19.901829-05
862aeea7-2222-4c5c-be76-1f46291bc768	\N	\N	73	page_visit	Visited availability page	\N	\N	192.168.1.68	Mozilla/5.0 (Windows NT 10.0; Win64; x64)	{"page": "availability", "duration": 289}	2025-06-10 08:04:59.901829-05
61da0fa7-021e-46f0-aa48-bdc3c8f501c6	165596	2908	52	lineup_update	Team lineup was updated	\N	\N	192.168.1.223	Mozilla/5.0 (Windows NT 10.0; Win64; x64)	\N	2025-06-09 17:03:55.917503-05
e2e2a4d3-3126-40c4-a38b-41a344618652	\N	\N	43	data_update	Data was updated in system	\N	\N	192.168.1.175	Mozilla/5.0 (Windows NT 10.0; Win64; x64)	\N	2025-06-09 19:39:25.917503-05
b590ffa4-f9ad-4634-ad62-e3a0ddc4848c	165587	\N	70	logout	User logged out of Rally app	\N	\N	192.168.1.238	Mozilla/5.0 (iPhone; CPU iPhone OS 15_0 like Mac OS X)	\N	2025-06-09 19:28:01.917503-05
efb85dba-b0ac-4157-ba43-67c69a58db98	165586	\N	49	admin_action	Admin performed data import	\N	\N	192.168.1.13	Mozilla/5.0 (iPad; CPU OS 15_0 like Mac OS X)	\N	2025-06-09 09:14:35.917503-05
586455c9-bc9f-4f25-adbe-b69f5c883ba5	165596	\N	74	team_email	Team email was sent	\N	\N	192.168.1.133	Mozilla/5.0 (Windows NT 10.0; Win64; x64)	\N	2025-06-09 09:57:44.917503-05
417b6b21-d40c-41ee-8cb7-dd7b8d62263e	\N	2910	74	availability_update	Availability updated to unavailable	\N	\N	192.168.1.249	Mozilla/5.0 (Windows NT 10.0; Win64; x64)	\N	2025-06-08 18:11:18.935206-05
142c9bf4-1ede-44fb-80f6-95291de58626	165579	\N	73	availability_update	Lisa Korach marked as available	\N	\N	192.168.1.190	Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)	\N	2025-06-07 11:54:50.940444-05
2b931f92-447d-4815-8803-f88518e9b0ba	165582	\N	74	team_email	Team email was sent	\N	\N	192.168.1.29	Mozilla/5.0 (iPhone; CPU iPhone OS 15_0 like Mac OS X)	\N	2025-06-07 09:10:52.940444-05
2f1ff1e7-4eea-4f90-be82-a5c9676118e4	165584	2916	52	team_email	Team email was sent	\N	\N	192.168.1.45	Mozilla/5.0 (iPad; CPU OS 15_0 like Mac OS X)	\N	2025-06-07 13:39:24.940444-05
87318de0-0318-4700-a99f-4def6820e402	\N	2908	50	logout	User logged out of Rally app	\N	\N	192.168.1.1	Mozilla/5.0 (iPhone; CPU iPhone OS 15_0 like Mac OS X)	\N	2025-06-06 20:17:59.951063-05
fb76c985-ec2a-4635-aa9c-6a270a9030ad	\N	\N	52	availability_update	Availability updated to maybe	\N	\N	192.168.1.9	Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)	\N	2025-06-06 20:48:42.951063-05
3019f62a-2937-44f8-af87-d1219b12d61d	165593	2915	51	page_visit	Visited lineup page	\N	\N	192.168.1.160	Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)	{"page": "schedule", "duration": 238}	2025-06-06 15:19:06.951063-05
afc5e3c1-c75a-4c95-b8e0-5a70a1a1a4d3	\N	2917	52	availability_update	Availability updated to maybe	\N	\N	192.168.1.224	Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)	\N	2025-06-05 19:18:32.963291-05
f385c3d0-c09d-49c9-9bae-4d6b7219b371	\N	2910	52	availability_update	Availability updated to maybe	\N	\N	192.168.1.249	Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)	\N	2025-06-05 22:07:30.963291-05
0775f471-c19b-4b90-87f1-2139f80b2234	165587	\N	70	login	User Dave Israel logged in	\N	\N	192.168.1.35	Mozilla/5.0 (iPhone; CPU iPhone OS 15_0 like Mac OS X)	\N	2025-06-05 16:54:17.963291-05
5e9f1007-4b07-4722-9d91-178086f48615	165581	2914	50	poll_response	Debbie Goldstein responded to team poll	896	poll	192.168.1.124	Mozilla/5.0 (Windows NT 10.0; Win64; x64)	\N	2025-06-05 21:19:48.963291-05
3b9d94ea-da5a-4b03-999f-80c8aeff814b	\N	2910	74	lineup_update	Team lineup was updated	\N	\N	192.168.1.81	Mozilla/5.0 (iPhone; CPU iPhone OS 15_0 like Mac OS X)	\N	2025-06-05 12:19:05.963291-05
bb20b631-941d-4404-930c-06343b6a76c6	\N	2914	51	lineup_update	Team lineup was updated	\N	\N	192.168.1.89	Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)	\N	2025-06-05 16:51:30.963291-05
21199339-75ad-4c32-8509-dfc5b28abef5	165579	2910	43	availability_update	Lisa Korach marked as unavailable	\N	\N	192.168.1.160	Mozilla/5.0 (iPhone; CPU iPhone OS 15_0 like Mac OS X)	\N	2025-06-05 10:58:46.963291-05
63cf8758-c406-4620-8248-ca1186989d81	165589	2910	52	data_update	Data was updated in system	\N	\N	192.168.1.216	Mozilla/5.0 (Windows NT 10.0; Win64; x64)	\N	2025-06-05 21:49:07.963291-05
e57adb18-8c45-4249-a469-bcd7404bd2f9	\N	\N	52	team_email	Team email was sent	\N	\N	192.168.1.58	Mozilla/5.0 (Windows NT 10.0; Win64; x64)	\N	2025-06-05 18:37:18.963291-05
d2f3aacb-eb32-407f-bdf4-599649b06550	165582	2913	74	score_submitted	Match score was submitted	3769	match	192.168.1.113	Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)	\N	2025-06-05 17:05:39.963291-05
30b1e219-d719-49fe-b770-a538acf62f6e	165586	\N	72	admin_action	Admin performed data import	\N	\N	192.168.1.123	Mozilla/5.0 (Windows NT 10.0; Win64; x64)	\N	2025-06-05 11:01:34.963291-05
8c209c61-1471-4be5-87c8-99ec161c310e	165583	\N	72	team_email	Team email was sent	\N	\N	192.168.1.59	Mozilla/5.0 (iPhone; CPU iPhone OS 15_0 like Mac OS X)	\N	2025-06-04 15:03:00.999049-05
4f4ac933-ea86-4968-bb4f-af172c33ba51	165583	2914	51	poll_response	Susan Kramer responded to team poll	411	poll	192.168.1.92	Mozilla/5.0 (Windows NT 10.0; Win64; x64)	\N	2025-06-04 20:50:00.999049-05
4a5d084f-3a0a-4e49-a8d0-35a97499ad4a	165581	\N	50	dashboard_access	Admin accessed activity dashboard	\N	\N	192.168.1.42	Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)	\N	2025-06-04 17:44:40.999049-05
23fa713a-deb1-47d9-a353-74829e5a8bbd	165590	\N	73	poll_response	Chris O'Malley responded to team poll	494	poll	192.168.1.164	Mozilla/5.0 (Windows NT 10.0; Win64; x64)	\N	2025-06-04 15:04:52.999049-05
11ddeaa6-122d-4493-8de6-4b3f6eed0c7f	165587	\N	70	logout	User logged out of Rally app	\N	\N	192.168.1.45	Mozilla/5.0 (iPhone; CPU iPhone OS 15_0 like Mac OS X)	\N	2025-06-04 20:00:44.999049-05
af6806f1-d29b-4367-bfdd-f99c439b5264	165592	2911	51	lineup_update	Team lineup was updated	\N	\N	192.168.1.210	Mozilla/5.0 (iPad; CPU OS 15_0 like Mac OS X)	\N	2025-06-04 13:52:52.999049-05
6fe98bd3-2903-4c65-b221-e8203db58047	\N	2908	50	page_visit	Visited availability page	\N	\N	192.168.1.141	Mozilla/5.0 (iPhone; CPU iPhone OS 15_0 like Mac OS X)	{"page": "availability", "duration": 59}	2025-06-04 19:59:31.999049-05
fad4a9b1-aeaa-4d90-9475-47ce4f1dc464	\N	2911	51	data_update	Data was updated in system	\N	\N	192.168.1.83	Mozilla/5.0 (iPad; CPU OS 15_0 like Mac OS X)	\N	2025-06-04 18:29:40.999049-05
cc9760b4-81cd-47c3-bc41-ec93e2fe085b	165596	\N	51	data_update	Data was updated in system	\N	\N	192.168.1.58	Mozilla/5.0 (Windows NT 10.0; Win64; x64)	\N	2025-06-03 12:40:59.020084-05
079eaf11-1557-47f3-ac96-60bb8765ca51	\N	2912	51	page_visit	Visited availability page	\N	\N	192.168.1.16	Mozilla/5.0 (iPad; CPU OS 15_0 like Mac OS X)	{"page": "availability", "duration": 95}	2025-06-03 16:17:50.020084-05
b6ff975e-5659-4664-bfec-d8893e95542c	165579	2912	73	login	User Allen Guon logged in	\N	\N	192.168.1.39	Mozilla/5.0 (iPad; CPU OS 15_0 like Mac OS X)	\N	2025-06-03 20:28:57.020084-05
dc1e1584-9bac-4696-b7be-03bd70e5ac56	165588	\N	70	match_created	Match result created for team	5568	match	192.168.1.88	Mozilla/5.0 (iPad; CPU OS 15_0 like Mac OS X)	{"home_score": 3, "away_score": 0}	2025-06-03 20:41:56.020084-05
65c98e91-88f9-459e-ae12-afad2d26ed2a	\N	2917	50	page_visit	Visited team_stats page	\N	\N	192.168.1.141	Mozilla/5.0 (iPhone; CPU iPhone OS 15_0 like Mac OS X)	{"page": "lineup", "duration": 85}	2025-06-03 21:03:23.020084-05
e68dba52-7240-43bc-89ea-15a29e4291c3	165588	2915	74	score_submitted	Match score was submitted	9248	match	192.168.1.224	Mozilla/5.0 (iPad; CPU OS 15_0 like Mac OS X)	\N	2025-06-03 12:20:49.020084-05
0fb2ebcc-0b8e-437b-bf43-d6d45f5d53b6	165589	\N	73	page_visit	Visited lineup page	\N	\N	192.168.1.169	Mozilla/5.0 (iPad; CPU OS 15_0 like Mac OS X)	{"page": "availability", "duration": 121}	2025-06-03 16:23:44.020084-05
3fbff109-278e-452c-b5da-75d9880bd801	165596	\N	74	score_submitted	Match score was submitted	2510	match	192.168.1.186	Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)	\N	2025-06-03 22:40:01.020084-05
0e703f84-75cd-4c31-bb0d-d173bfcfa245	165591	2913	72	lineup_update	Team lineup was updated	\N	\N	192.168.1.172	Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)	\N	2025-06-03 08:30:13.020084-05
ee2ee63f-5272-49e6-b30d-9ac6a43ff94f	165596	\N	74	logout	User logged out of Rally app	\N	\N	192.168.1.178	Mozilla/5.0 (iPad; CPU OS 15_0 like Mac OS X)	\N	2025-06-02 19:11:53.050794-05
6c1d253f-b5b6-456a-b00d-f6df269031b0	\N	2911	73	poll_response	Team poll response received	789	poll	192.168.1.37	Mozilla/5.0 (iPad; CPU OS 15_0 like Mac OS X)	\N	2025-06-02 15:25:58.050794-05
0d65bc95-f122-48af-b910-aceae94897e7	\N	\N	51	poll_response	Team poll response received	182	poll	192.168.1.194	Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)	\N	2025-06-02 19:06:08.050794-05
cad5ac56-75c0-4de9-b2c7-5b369d056e50	165582	\N	43	availability_update	Leslie Katz marked as unavailable	\N	\N	192.168.1.122	Mozilla/5.0 (iPhone; CPU iPhone OS 15_0 like Mac OS X)	\N	2025-06-02 09:54:26.050794-05
e3d34d52-9cf0-4e0c-a7a1-975974b05872	165590	2910	70	page_visit	Visited matches page	\N	\N	192.168.1.141	Mozilla/5.0 (iPad; CPU OS 15_0 like Mac OS X)	{"page": "lineup", "duration": 44}	2025-06-02 21:30:31.050794-05
24d9b11b-ff17-4ebc-b615-463bc209f32f	165586	2913	73	admin_action	Admin performed league update	\N	\N	192.168.1.41	Mozilla/5.0 (iPhone; CPU iPhone OS 15_0 like Mac OS X)	\N	2025-06-01 14:41:46.064953-05
d22b5b7f-fcfe-42ba-97b0-6bc266139b59	165597	2915	49	poll_response	Christine Neuman responded to team poll	180	poll	192.168.1.66	Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)	\N	2025-06-01 13:23:53.064953-05
ab2535cc-589a-4f3f-b276-6d91a9259fc4	165583	2917	72	login	User Scott Osterman logged in	\N	\N	192.168.1.203	Mozilla/5.0 (Windows NT 10.0; Win64; x64)	\N	2025-06-01 12:07:23.064953-05
84fec642-14d6-4dfb-8e65-a7b36687dc33	\N	\N	43	page_visit	Visited availability page	\N	\N	192.168.1.176	Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)	{"page": "lineup", "duration": 271}	2025-05-31 22:40:41.076065-05
633346e2-20e8-4bc6-a6f6-078999d97e22	\N	2913	49	match_created	Match result created for Biltmore CC - 21	9084	match	192.168.1.235	Mozilla/5.0 (Windows NT 10.0; Win64; x64)	{"home_score": 2, "away_score": 3}	2025-05-31 18:48:15.076065-05
144bce62-a68e-4f98-b87c-97cf814518c7	165586	2909	72	data_update	Data was updated in system	\N	\N	192.168.1.228	Mozilla/5.0 (iPhone; CPU iPhone OS 15_0 like Mac OS X)	\N	2025-05-31 10:43:04.076065-05
c495aee1-4d91-4b7b-b8d6-2bfa72eb0b07	165583	2915	51	score_submitted	Match score was submitted	2937	match	192.168.1.213	Mozilla/5.0 (iPad; CPU OS 15_0 like Mac OS X)	\N	2025-05-31 09:24:13.076065-05
f42e97b7-08a6-4842-8da3-2eb9ee381ed0	\N	\N	49	logout	User logged out of Rally app	\N	\N	192.168.1.156	Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)	\N	2025-05-31 16:57:24.076065-05
09b9dd7d-8a8c-4ffd-aba8-1b58e57590d1	165587	2908	51	match_created	Match result created for Barrington Hills CC - 11	1902	match	192.168.1.177	Mozilla/5.0 (iPhone; CPU iPhone OS 15_0 like Mac OS X)	{"home_score": 3, "away_score": 0}	2025-05-31 15:41:47.076065-05
a8294b68-ae14-4af4-81dc-ba35642c7ec6	165581	\N	72	page_visit	Visited availability page	\N	\N	192.168.1.22	Mozilla/5.0 (iPad; CPU OS 15_0 like Mac OS X)	{"page": "schedule", "duration": 170}	2025-05-31 10:01:55.076065-05
60b511a7-02ef-437e-abab-858abccfaed5	\N	\N	50	match_created	Match result created for team	1156	match	192.168.1.223	Mozilla/5.0 (iPhone; CPU iPhone OS 15_0 like Mac OS X)	{"home_score": 4, "away_score": 2}	2025-05-31 22:00:12.076065-05
0ac650a3-33f1-4531-9d03-b7cbfe7587e7	\N	\N	49	data_update	Data was updated in system	\N	\N	192.168.1.4	Mozilla/5.0 (iPhone; CPU iPhone OS 15_0 like Mac OS X)	\N	2025-05-30 14:46:57.098225-05
66a8387d-4bc4-472b-a7df-686d31951766	165579	\N	43	page_visit	Visited availability page	\N	\N	192.168.1.32	Mozilla/5.0 (Windows NT 10.0; Win64; x64)	{"page": "availability", "duration": 235}	2025-05-30 15:20:21.098225-05
c4786def-5b34-4784-b063-1b7ba7a38ee1	165594	2916	52	score_submitted	Match score was submitted	4756	match	192.168.1.152	Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)	\N	2025-05-29 13:41:30.103825-05
25f607b0-e925-45b4-8a8d-1faf4f6a6c8d	165594	2913	73	score_submitted	Match score was submitted	2602	match	192.168.1.119	Mozilla/5.0 (iPad; CPU OS 15_0 like Mac OS X)	\N	2025-05-29 08:04:50.103825-05
d0ba158e-b83c-4ad7-891e-482328457add	165583	\N	51	match_created	Match result created for team	5883	match	192.168.1.138	Mozilla/5.0 (iPad; CPU OS 15_0 like Mac OS X)	{"home_score": 6, "away_score": 3}	2025-05-29 10:41:40.103825-05
73f28a1a-b214-4c36-ae74-a66846c4d319	165579	2916	51	team_email	Team email was sent	\N	\N	192.168.1.154	Mozilla/5.0 (iPhone; CPU iPhone OS 15_0 like Mac OS X)	\N	2025-05-28 18:04:36.112538-05
61041942-be9b-4836-a07d-4498a7f8e8d6	165591	2913	74	poll_response	Melissa Burke responded to team poll	868	poll	192.168.1.19	Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)	\N	2025-05-28 08:20:20.112538-05
3cb608df-977d-4d6c-a5b5-8168e9f85e3e	165589	\N	43	poll_response	Svetlana Schroeder responded to team poll	888	poll	192.168.1.251	Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)	\N	2025-05-28 12:31:22.112538-05
a90c4309-7ef6-4788-8342-4cbcf0591c54	165590	\N	73	score_submitted	Match score was submitted	2296	match	192.168.1.221	Mozilla/5.0 (iPad; CPU OS 15_0 like Mac OS X)	\N	2025-05-27 21:13:39.120918-05
43261b7e-aabe-4fac-9585-327bb43fc9d6	165597	2912	73	login	User Allen Guon logged in	\N	\N	192.168.1.3	Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)	\N	2025-05-27 17:06:52.120918-05
5d79b428-fe12-46ff-919c-66a10e2e6ffb	165586	\N	72	logout	User logged out of Rally app	\N	\N	192.168.1.153	Mozilla/5.0 (Windows NT 10.0; Win64; x64)	\N	2025-05-27 12:46:27.120918-05
edd04eae-446b-4fe4-860b-79c4cceaa70c	165585	2915	72	score_submitted	Match score was submitted	9788	match	192.168.1.68	Mozilla/5.0 (Windows NT 10.0; Win64; x64)	\N	2025-05-27 11:21:18.120918-05
54ab8af0-e1d5-4a9b-892c-d36898c5a33a	\N	2911	51	lineup_update	Team lineup was updated	\N	\N	192.168.1.46	Mozilla/5.0 (iPad; CPU OS 15_0 like Mac OS X)	\N	2025-05-27 13:52:15.120918-05
5c02292c-0232-4400-906c-b862856ace55	\N	2915	74	team_email	Team email was sent	\N	\N	192.168.1.79	Mozilla/5.0 (Windows NT 10.0; Win64; x64)	\N	2025-05-27 08:17:37.120918-05
2363e3bc-321a-4b6b-a78b-d601a6be4194	\N	2911	49	data_update	Data was updated in system	\N	\N	192.168.1.6	Mozilla/5.0 (Windows NT 10.0; Win64; x64)	\N	2025-05-27 19:25:29.120918-05
a86821bc-6edf-428d-801c-21625a4e4e6c	165589	2914	51	admin_action	Admin performed user management	\N	\N	192.168.1.131	Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)	\N	2025-05-27 11:40:41.120918-05
9c5a0ae8-009d-4e3b-9bb3-9665a67e1816	\N	\N	49	page_visit	Visited schedule page	\N	\N	192.168.1.229	Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)	{"page": "lineup", "duration": 200}	2025-05-27 12:53:46.120918-05
594e00b9-c67a-4633-a23b-7ea05b649eb0	165596	\N	73	match_created	Match result created for team	9746	match	192.168.1.69	Mozilla/5.0 (Windows NT 10.0; Win64; x64)	{"home_score": 3, "away_score": 5}	2025-05-27 21:30:19.120918-05
0a180008-5fa2-408e-8d14-03c18be57d4e	165580	\N	51	poll_response	Samantha Borstein responded to team poll	154	poll	192.168.1.16	Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)	\N	2025-05-26 12:07:12.150809-05
b25efb05-761c-49ef-864b-1a93facddebc	165593	\N	51	match_created	Match result created for team	1919	match	192.168.1.9	Mozilla/5.0 (iPad; CPU OS 15_0 like Mac OS X)	{"home_score": 4, "away_score": 0}	2025-05-26 08:43:21.150809-05
feedd222-f1b0-4cf4-b959-58840964b98b	\N	\N	72	dashboard_access	Admin accessed activity dashboard	\N	\N	192.168.1.5	Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)	\N	2025-05-26 13:33:45.150809-05
02239fc4-9b01-4e9c-8bf5-0b8aaf7f9427	165581	\N	52	dashboard_access	Admin accessed activity dashboard	\N	\N	192.168.1.201	Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)	\N	2025-05-26 10:46:43.150809-05
9655794a-c0a7-442b-9457-669219c2484f	165585	\N	51	team_email	Team email was sent	\N	\N	192.168.1.68	Mozilla/5.0 (Windows NT 10.0; Win64; x64)	\N	2025-05-25 16:51:43.161547-05
91f25b99-8c4a-4943-bed6-ec8b85df8e96	\N	2917	73	match_created	Match result created for Birchwood - 13	1808	match	192.168.1.213	Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)	{"home_score": 4, "away_score": 3}	2025-05-25 08:39:59.161547-05
93f377ea-137c-4c09-ae63-9277593eff5a	165585	\N	72	score_submitted	Match score was submitted	4012	match	192.168.1.247	Mozilla/5.0 (Windows NT 10.0; Win64; x64)	\N	2025-05-25 14:31:21.161547-05
974634e2-379e-41a4-9442-d7e74191047a	165578	\N	70	logout	User logged out of Rally app	\N	\N	192.168.1.181	Mozilla/5.0 (iPad; CPU OS 15_0 like Mac OS X)	\N	2025-05-25 20:22:01.161547-05
aae11a72-c112-4220-bd92-3cf274805b24	165584	2913	49	lineup_update	Team lineup was updated	\N	\N	192.168.1.10	Mozilla/5.0 (iPhone; CPU iPhone OS 15_0 like Mac OS X)	\N	2025-05-25 13:47:38.161547-05
4f234965-8534-4fed-91bd-b0f408b3f642	165587	2915	51	logout	User logged out of Rally app	\N	\N	192.168.1.184	Mozilla/5.0 (iPad; CPU OS 15_0 like Mac OS X)	\N	2025-05-25 12:18:01.161547-05
8f38b74d-6413-4e8f-994d-8cfef61b0d2a	165594	2915	51	team_email	Team email was sent	\N	\N	192.168.1.5	Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)	\N	2025-05-25 18:02:58.161547-05
6a1976ad-3579-4669-9ef7-02d78a6a4d66	165578	2909	52	login	User Mike Borchew logged in	\N	\N	192.168.1.180	Mozilla/5.0 (Windows NT 10.0; Win64; x64)	\N	2025-05-25 14:17:52.161547-05
be836b96-8c88-439d-9a3d-0df49ff572db	\N	\N	70	page_visit	Visited improve page	\N	\N	192.168.1.141	Mozilla/5.0 (iPad; CPU OS 15_0 like Mac OS X)	{"page": "availability", "duration": 262}	2025-05-25 18:25:32.161547-05
56708dd7-882b-4665-b100-9666d66772ea	165593	\N	74	admin_action	Admin performed data import	\N	\N	192.168.1.115	Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)	\N	2025-05-25 10:27:39.161547-05
51aff217-3694-4db0-be35-7bb1cf10ccae	\N	\N	43	data_update	Data was updated in system	\N	\N	192.168.1.12	Mozilla/5.0 (iPhone; CPU iPhone OS 15_0 like Mac OS X)	\N	2025-05-25 13:29:17.161547-05
fcf5ea7e-5cfe-4cfe-b8fb-e5e1c77ccfc4	165586	\N	52	dashboard_access	Admin accessed activity dashboard	\N	\N	192.168.1.55	Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)	\N	2025-05-25 12:32:05.161547-05
591570a2-3aa6-464e-a546-973f6c79a385	\N	2913	73	login	User Allen Guon logged in	\N	\N	192.168.1.67	Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)	\N	2025-05-24 16:22:56.199277-05
57262b78-26e7-48e7-ba68-f6a874c4fe2d	\N	\N	50	lineup_update	Team lineup was updated	\N	\N	192.168.1.249	Mozilla/5.0 (Windows NT 10.0; Win64; x64)	\N	2025-05-24 08:01:22.199277-05
7ce0e430-83fa-4118-b082-56cb3a257c8a	165592	2911	70	data_update	Data was updated in system	\N	\N	192.168.1.91	Mozilla/5.0 (iPad; CPU OS 15_0 like Mac OS X)	\N	2025-05-24 10:54:22.199277-05
954bd5f6-af0e-45a5-bc69-a6fc4f0a5522	165589	\N	49	lineup_update	Team lineup was updated	\N	\N	192.168.1.3	Mozilla/5.0 (Windows NT 10.0; Win64; x64)	\N	2025-05-24 08:33:50.199277-05
07a01985-6d3b-4923-a9f1-786d462d4bd4	\N	\N	51	dashboard_access	Admin accessed activity dashboard	\N	\N	192.168.1.146	Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)	\N	2025-05-24 22:07:15.199277-05
37b40bf6-eef2-47c9-8034-73155036706c	165586	2915	50	team_email	Team email was sent	\N	\N	192.168.1.223	Mozilla/5.0 (iPad; CPU OS 15_0 like Mac OS X)	\N	2025-05-24 08:46:33.199277-05
e900da57-9d70-4200-9428-74b4314af6d9	165583	\N	50	page_visit	Visited availability page	\N	\N	192.168.1.104	Mozilla/5.0 (Windows NT 10.0; Win64; x64)	{"page": "lineup", "duration": 40}	2025-05-24 08:04:04.199277-05
0ad51c5a-0a28-4932-b70a-8580815e6f1d	\N	2917	52	team_email	Team email was sent	\N	\N	192.168.1.196	Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)	\N	2025-05-24 10:59:26.199277-05
e0688632-3d02-4e34-b9ae-18be623da909	165589	2915	50	login	User Adam Seyb logged in	\N	\N	192.168.1.186	Mozilla/5.0 (iPad; CPU OS 15_0 like Mac OS X)	\N	2025-05-24 15:23:07.199277-05
cc268a94-407f-4277-a541-8dcbfc15ac58	165584	2914	43	logout	User logged out of Rally app	\N	\N	192.168.1.125	Mozilla/5.0 (iPhone; CPU iPhone OS 15_0 like Mac OS X)	\N	2025-05-24 14:21:40.199277-05
8afd229f-d5f8-4d7a-bc64-01bdb67cccd4	\N	2915	70	score_submitted	Match score was submitted	3312	match	192.168.1.161	Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)	\N	2025-05-24 21:22:41.199277-05
e4009021-eecd-4e7f-815e-77a82cd28b69	165582	2909	74	login	User Brian Stutland logged in	\N	\N	192.168.1.114	Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)	\N	2025-05-24 16:11:39.199277-05
018bd116-d020-4521-9801-7332baa5d51c	165581	2914	49	poll_response	Debbie Goldstein responded to team poll	129	poll	192.168.1.56	Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)	\N	2025-05-23 16:36:41.231649-05
1483c452-9a68-4efc-aeef-f10d175ad8b4	\N	\N	51	score_submitted	Match score was submitted	3572	match	192.168.1.150	Mozilla/5.0 (Windows NT 10.0; Win64; x64)	\N	2025-05-23 22:14:07.231649-05
2ef1c2e1-9245-4873-821c-428370172f92	165589	\N	49	match_created	Match result created for team	4527	match	192.168.1.143	Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)	{"home_score": 6, "away_score": 4}	2025-05-23 14:01:57.231649-05
5f7e9bd6-411d-41aa-a3f7-867506c6d2b1	165591	\N	74	admin_action	Admin performed user management	\N	\N	192.168.1.189	Mozilla/5.0 (iPhone; CPU iPhone OS 15_0 like Mac OS X)	\N	2025-05-23 17:21:00.231649-05
0e525c89-28dd-402b-a0e0-218cb1afd38d	\N	2914	43	availability_update	Availability updated to unavailable	\N	\N	192.168.1.21	Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)	\N	2025-05-23 12:57:10.231649-05
22a81def-8698-4a8a-9123-d3db829358d2	165590	2915	72	login	User Scott Osterman logged in	\N	\N	192.168.1.252	Mozilla/5.0 (Windows NT 10.0; Win64; x64)	\N	2025-05-22 20:44:44.24902-05
8b924367-ae8e-43b8-b7e8-af16bd32393d	165590	2917	73	login	User Allen Guon logged in	\N	\N	192.168.1.215	Mozilla/5.0 (iPhone; CPU iPhone OS 15_0 like Mac OS X)	\N	2025-05-22 20:14:53.24902-05
dafcd0db-7737-4832-a68e-971effc6bdcc	172778	\N	43	login	User Ross Freedman logged in successfully	\N	\N	\N	\N	{"associated_players_count": 2, "has_primary_player": true, "primary_player_club": "Tennaqua", "primary_player_series": "Chicago 22"}	2025-06-20 16:15:58.531666-05
a6a71690-eedb-488f-aa08-39098fca37d9	\N	\N	43	page_visit	Visited Admin Activity Dashboard page	\N	\N	127.0.0.1	Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/137.0.0.0 Safari/537.36	{"page": "admin_dashboard", "page_category": "admin", "details": "Admin accessed activity monitoring dashboard"}	2025-06-20 16:16:15.582791-05
5f72ae03-c029-4b1f-a68e-c338e0e0504c	167406	\N	76	login	User Lisa Wagner logged in successfully	\N	\N	\N	\N	{"associated_players_count": 1, "has_primary_player": true, "primary_player_club": "Tennaqua", "primary_player_series": "Division 12"}	2025-06-20 16:19:39.086058-05
3f9d0c1a-911b-4161-a50a-f1d118c113fa	172778	\N	43	login	User Ross Freedman logged in successfully	\N	\N	\N	\N	{"associated_players_count": 2, "has_primary_player": true, "primary_player_club": "Tennaqua", "primary_player_series": "Chicago 22"}	2025-06-20 16:24:08.83054-05
5af1b439-1385-48e5-acec-4d4958b5ab18	\N	\N	43	page_visit	Visited Admin Activity Dashboard page	\N	\N	127.0.0.1	Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/137.0.0.0 Safari/537.36	{"page": "admin_dashboard", "page_category": "admin", "details": "Admin accessed activity monitoring dashboard"}	2025-06-20 16:24:13.566177-05
46da0bdd-5296-4f15-8d1f-94a6a4bcf52e	172778	\N	43	availability_update	Updated availability for 2024-09-24 to available	1724	series	127.0.0.1	Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/137.0.0.0 Safari/537.36	{"match_date": "2024-09-24", "availability_status": 1, "status_text": "available", "player_name": "Ross Freedman", "tenniscores_player_id": "nndz-WkMrK3didjlnUT09", "series_id": 1724, "notes": "", "was_new_record": true}	2025-06-20 16:25:02.02459-05
6a73df16-cfca-439d-a499-65577cc173bb	\N	\N	43	page_visit	Visited Admin Activity Dashboard page	\N	\N	127.0.0.1	Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/137.0.0.0 Safari/537.36	{"page": "admin_dashboard", "page_category": "admin", "details": "Admin accessed activity monitoring dashboard"}	2025-06-20 16:31:58.711599-05
38b7f711-deb3-4fe9-9aad-85ef4b8aa120	\N	\N	43	page_visit	Visited Admin Activity Dashboard page	\N	\N	127.0.0.1	Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/137.0.0.0 Safari/537.36	{"page": "admin_dashboard", "page_category": "admin", "details": "Admin accessed activity monitoring dashboard"}	2025-06-20 16:32:30.580338-05
94e30292-0665-427c-9c1d-c9e38f384b59	183076	\N	43	login	User Ross Freedman logged in successfully	\N	\N	\N	\N	{"associated_players_count": 2, "has_primary_player": true, "primary_player_club": "Tennaqua", "primary_player_series": "Chicago 22"}	2025-06-21 11:20:15.359105-05
2db8a45c-e7b8-49c8-88a9-a5eea4d8d7cc	\N	\N	43	page_visit	Visited Admin Activity Dashboard page	\N	\N	127.0.0.1	Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/137.0.0.0 Safari/537.36	{"page": "admin_dashboard", "page_category": "admin", "details": "Admin accessed activity monitoring dashboard"}	2025-06-20 16:37:48.682781-05
17340e57-1b6d-4325-baad-699753a01681	\N	\N	43	page_visit	Visited Admin Activity Dashboard page	\N	\N	127.0.0.1	Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/137.0.0.0 Safari/537.36	{"page": "admin_dashboard", "page_category": "admin", "details": "Admin accessed activity monitoring dashboard"}	2025-06-20 16:39:25.305551-05
926e00a7-da08-443f-ab1d-184d853892c9	172778	\N	43	login	User Ross Freedman logged in successfully	\N	\N	\N	\N	{"associated_players_count": 2, "has_primary_player": true, "primary_player_club": "Tennaqua", "primary_player_series": "Chicago 22"}	2025-06-20 16:40:21.156768-05
0f3f20c8-017b-4e40-8d29-a046678b9ff6	\N	\N	43	page_visit	Visited Admin Activity Dashboard page	\N	\N	127.0.0.1	Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/137.0.0.0 Safari/537.36	{"page": "admin_dashboard", "page_category": "admin", "details": "Admin accessed activity monitoring dashboard"}	2025-06-20 16:40:23.649299-05
8caa5ba2-3227-47ac-ab71-6484352111db	\N	\N	43	page_visit	Visited Admin Activity Dashboard page	\N	\N	127.0.0.1	Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/137.0.0.0 Safari/537.36	{"page": "admin_dashboard", "page_category": "admin", "details": "Admin accessed activity monitoring dashboard"}	2025-06-20 16:41:51.222896-05
656960a9-ead6-4c1a-9a18-b90e5a016ac8	\N	\N	43	page_visit	Visited Admin Activity Dashboard page	\N	\N	127.0.0.1	Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/137.0.0.0 Safari/537.36	{"page": "admin_dashboard", "page_category": "admin", "details": "Admin accessed activity monitoring dashboard"}	2025-06-20 17:19:06.802977-05
41c15146-1a3b-4dbf-86c2-2e712db4572a	172778	\N	43	availability_update	Updated availability for 2024-10-01 to unavailable	1724	series	127.0.0.1	Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/137.0.0.0 Safari/537.36	{"match_date": "2024-10-01", "availability_status": 2, "status_text": "unavailable", "player_name": "Ross Freedman", "tenniscores_player_id": "nndz-WkMrK3didjlnUT09", "series_id": 1724, "notes": "", "was_new_record": true}	2025-06-20 17:21:48.411908-05
9aa58a3e-8c27-413e-842f-8e67205d67b4	\N	\N	43	page_visit	Visited Admin Activity Dashboard page	\N	\N	127.0.0.1	Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/137.0.0.0 Safari/537.36	{"page": "admin_dashboard", "page_category": "admin", "details": "Admin accessed activity monitoring dashboard"}	2025-06-20 17:21:54.969014-05
1c1d9841-b961-45eb-96ed-14782db7a7cd	172778	\N	43	login	User Ross Freedman logged in successfully	\N	\N	\N	\N	{"associated_players_count": 2, "has_primary_player": true, "primary_player_club": "Tennaqua", "primary_player_series": "Chicago 22"}	2025-06-21 06:31:59.996811-05
c1b2f031-dd14-4343-b723-e178ade5a2b2	\N	\N	43	page_visit	Visited Admin Activity Dashboard page	\N	\N	127.0.0.1	Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/137.0.0.0 Safari/537.36	{"page": "admin_dashboard", "page_category": "admin", "details": "Admin accessed activity monitoring dashboard"}	2025-06-21 07:07:17.893603-05
68ac4c26-ac7b-4cec-8079-738683826e36	172778	\N	43	availability_update	Updated availability for 2024-09-24 to available	1724	series	127.0.0.1	Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/137.0.0.0 Safari/537.36	{"match_date": "2024-09-24", "availability_status": 1, "status_text": "available", "player_name": "Ross Freedman", "tenniscores_player_id": "nndz-WkMrK3didjlnUT09", "series_id": 1724, "notes": "Test", "was_new_record": false}	2025-06-21 07:07:40.661987-05
800d96e2-bbc0-4b87-b0eb-47f40148b641	172778	\N	43	availability_update	Updated availability for 2024-09-24 to not sure	1724	series	127.0.0.1	Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/137.0.0.0 Safari/537.36	{"match_date": "2024-09-24", "availability_status": 3, "status_text": "not sure", "player_name": "Ross Freedman", "tenniscores_player_id": "nndz-WkMrK3didjlnUT09", "series_id": 1724, "notes": "", "was_new_record": false}	2025-06-21 07:07:41.971618-05
2da3f8b0-251d-4f80-b7ce-5560b5e1963a	\N	\N	43	page_visit	Visited Admin Activity Dashboard page	\N	\N	127.0.0.1	Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/137.0.0.0 Safari/537.36	{"page": "admin_dashboard", "page_category": "admin", "details": "Admin accessed activity monitoring dashboard"}	2025-06-21 07:08:40.35552-05
c7b9fdcc-3b46-4634-b455-1f2858230b90	177704	\N	76	login	User Lisa Wagner logged in successfully	\N	\N	\N	\N	{"associated_players_count": 1, "has_primary_player": true, "primary_player_club": "Tennaqua", "primary_player_series": "Division 12"}	2025-06-21 10:47:15.629874-05
e1261104-13e1-4160-a234-d7bd45b7dec2	183076	\N	43	login	User Ross Freedman logged in successfully	\N	\N	\N	\N	{"associated_players_count": 2, "has_primary_player": true, "primary_player_club": "Tennaqua", "primary_player_series": "Chicago 22"}	2025-06-21 11:07:07.487012-05
f5997afb-6a09-4dff-99ca-395bdaaa28c8	183076	\N	43	availability_update	Updated availability for 2024-09-24 to available	1812	series	127.0.0.1	Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/137.0.0.0 Safari/537.36	{"match_date": "2024-09-24", "availability_status": 1, "status_text": "available", "player_name": "Ross Freedman", "tenniscores_player_id": "nndz-WkMrK3didjlnUT09", "series_id": 1812, "notes": "", "was_new_record": true}	2025-06-21 11:07:48.114693-05
565506c6-8b60-49f5-b663-89c7bbc9db57	177704	\N	76	login	User Lisa Wagner logged in successfully	\N	\N	\N	\N	{"associated_players_count": 1, "has_primary_player": true, "primary_player_club": "Tennaqua", "primary_player_series": "Division 12"}	2025-06-21 11:11:45.958285-05
38894b3a-5589-4e42-ad41-76e8e3b6635f	177704	\N	76	availability_update	Updated availability for 2025-01-09 to available	1847	series	127.0.0.1	Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/137.0.0.0 Safari/537.36	{"match_date": "2025-01-09", "availability_status": 1, "status_text": "available", "player_name": "Lisa Wagner", "tenniscores_player_id": "nndz-WkM2eHhybi9qUT09", "series_id": 1847, "notes": "", "was_new_record": true}	2025-06-21 11:12:20.888332-05
ff057418-7b08-4b6a-8310-2a8c5df2a1ef	177704	\N	76	login	User Lisa Wagner logged in successfully	\N	\N	\N	\N	{"associated_players_count": 1, "has_primary_player": true, "primary_player_club": "Tennaqua", "primary_player_series": "Division 12"}	2025-06-21 11:20:40.11061-05
7a7f2834-e2e6-4ae6-81dd-a8728bcc6610	188660	\N	77	user_registration	New user Jessica Freedman registered successfully	\N	\N	\N	\N	{"association_result": "associated", "association_detail": "Player association created with exact match", "provided_league": "CNSWPL", "provided_club": "Tennaqua", "provided_series": "Division 16", "player_auto_linked": true}	2025-06-21 12:43:42.481916-05
70c09892-968d-40bb-92e3-852faff66ec4	193374	\N	43	login	User Ross Freedman logged in successfully	\N	\N	\N	\N	{"associated_players_count": 2, "has_primary_player": true, "primary_player_club": "Tennaqua", "primary_player_series": "Chicago 22"}	2025-06-21 13:10:27.793053-05
beb56292-02ff-432e-8063-5af40e1ce38b	188660	\N	77	login	User Jessica Freedman logged in successfully	\N	\N	\N	\N	{"associated_players_count": 1, "has_primary_player": true, "primary_player_club": "Tennaqua", "primary_player_series": "Division 16"}	2025-06-21 13:11:39.785593-05
ba333f62-0b9d-40ac-83a6-29277fd188a4	193374	\N	43	login	User Ross Freedman logged in successfully	\N	\N	\N	\N	{"associated_players_count": 2, "has_primary_player": true, "primary_player_club": "Tennaqua", "primary_player_series": "Chicago 22"}	2025-06-21 13:29:49.76667-05
25ef62cf-ebfb-4b57-b7a6-95d05118653c	188660	\N	77	login	User Jessica Freedman logged in successfully	\N	\N	\N	\N	{"associated_players_count": 1, "has_primary_player": true, "primary_player_club": "Tennaqua", "primary_player_series": "Division 16"}	2025-06-21 13:30:09.516596-05
8e8ee1d9-1350-460e-bfbd-27c4d4ed7818	188002	\N	76	login	User Lisa Wagner logged in successfully	\N	\N	\N	\N	{"associated_players_count": 1, "has_primary_player": true, "primary_player_club": "Tennaqua", "primary_player_series": "Division 12"}	2025-06-21 13:34:41.848221-05
feff87a0-fb4b-44a2-9c37-b2b1fef6a317	198958	\N	77	login	User Jessica Freedman logged in successfully	\N	\N	\N	\N	{"associated_players_count": 1, "has_primary_player": true, "primary_player_club": "Tennaqua", "primary_player_series": "Division 16"}	2025-06-21 13:44:08.063318-05
a436d804-3b89-4435-b653-399e2cb8bc95	224268	\N	43	login	User Ross Freedman logged in successfully	\N	\N	\N	\N	{"associated_players_count": 2, "has_primary_player": true, "primary_player_club": "Tennaqua", "primary_player_series": "Chicago 22"}	2025-06-21 13:57:36.374886-05
33a5893e-1043-4347-bf18-51b42c89b203	219554	\N	77	login	User Jessica Freedman logged in successfully	\N	\N	\N	\N	{"associated_players_count": 1, "has_primary_player": true, "primary_player_club": "Tennaqua", "primary_player_series": "Division 16"}	2025-06-21 13:58:04.137449-05
61250d54-c0ef-4a14-8ad6-5a16ca36f4ad	229852	\N	77	login	User Jessica Freedman logged in successfully	\N	\N	\N	\N	{"associated_players_count": 1, "has_primary_player": true, "primary_player_club": "Tennaqua", "primary_player_series": "Division 16"}	2025-06-21 16:57:50.858754-05
03ed6fa7-3466-4f39-b92b-7a11acdb0ac3	229852	\N	77	availability_update	Updated availability for 2025-01-10 to available	2733	series	127.0.0.1	Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/137.0.0.0 Safari/537.36	{"match_date": "2025-01-10", "availability_status": 1, "status_text": "available", "player_name": "Jessica Freedman", "tenniscores_player_id": "nndz-WkMrK3dMMzdndz09", "series_id": 2733, "notes": "", "was_new_record": true}	2025-06-21 17:08:11.878385-05
b9bfdbf2-dc85-48f9-9cb0-fd2ace5bc65b	229852	\N	77	availability_update	Updated availability for 2025-01-10 to available	2733	series	127.0.0.1	Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/137.0.0.0 Safari/537.36	{"match_date": "2025-01-10", "availability_status": 1, "status_text": "available", "player_name": "Jessica Freedman", "tenniscores_player_id": "nndz-WkMrK3dMMzdndz09", "series_id": 2733, "notes": "Test", "was_new_record": false}	2025-06-21 17:08:23.50192-05
20f36557-0f20-47de-9828-3f251a89bd6c	249790	\N	76	login	User Lisa Wagner logged in successfully	\N	\N	\N	\N	{"associated_players_count": 1, "has_primary_player": true, "primary_player_club": "Tennaqua", "primary_player_series": "Division 12"}	2025-06-21 17:26:07.575861-05
99f6385a-0b38-4da3-ac4e-8f95660f1ead	271044	\N	77	login	User Jessica Freedman logged in successfully	\N	\N	\N	\N	{"associated_players_count": 1, "has_primary_player": true, "primary_player_club": "Tennaqua", "primary_player_series": "Division 16"}	2025-06-21 17:39:02.581485-05
c18d3186-4ab2-4944-bb47-9683bc6a4341	281342	\N	77	availability_update	Updated availability for 2025-01-10 to available	3174	series	127.0.0.1	Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/137.0.0.0 Safari/537.36	{"match_date": "2025-01-10", "availability_status": 1, "status_text": "available", "player_name": "Jessica Freedman", "tenniscores_player_id": "nndz-WkMrK3dMMzdndz09", "series_id": 3174, "notes": "", "was_new_record": true}	2025-06-21 17:42:04.027503-05
c8f92540-be18-49f3-844c-085196fb9bac	286056	\N	43	login	User Ross Freedman logged in successfully	\N	\N	\N	\N	{"associated_players_count": 2, "has_primary_player": true, "primary_player_club": "Tennaqua", "primary_player_series": "Chicago 22"}	2025-06-21 17:43:34.653189-05
e6dedc38-f4c6-4789-8e57-e6a8a6d8e9ba	301938	\N	77	login	User Jessica Freedman logged in successfully	\N	\N	\N	\N	{"associated_players_count": 1, "has_primary_player": true, "primary_player_club": "Tennaqua", "primary_player_series": "Division 16"}	2025-06-21 18:10:35.845329-05
19b0d1eb-5845-4c58-b4af-06c1f60ac4d1	312236	\N	77	login	User Jessica Freedman logged in successfully	\N	\N	\N	\N	{"associated_players_count": 1, "has_primary_player": true, "primary_player_club": "Tennaqua", "primary_player_series": "Division 16"}	2025-06-21 18:20:26.393449-05
a03a7cbd-3f9b-4f83-b86b-bf2cca2d9d83	311578	\N	76	login	User Lisa Wagner logged in successfully	\N	\N	\N	\N	{"associated_players_count": 1, "has_primary_player": true, "primary_player_club": "Tennaqua", "primary_player_series": "Division 12"}	2025-06-22 06:53:41.801675-05
9672f753-7dce-428d-a434-0a26e7218af0	\N	\N	79	user_registration	New user Aud Love registered successfully	\N	\N	\N	\N	{"association_result": "risky_matches_skipped", "association_detail": "Risky player matches found but skipped to avoid incorrect association", "provided_league": "CNSWPL", "provided_club": "Sunset Ridge", "provided_series": "Division 1", "player_auto_linked": false}	2025-06-22 06:56:26.113723-05
b273e67b-0b5f-4313-830a-77c7feeb0930	312245	\N	79	availability_update	Updated availability for 2025-01-10 to unavailable	3913	series	127.0.0.1	Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/137.0.0.0 Safari/537.36	{"match_date": "2025-01-10", "availability_status": 2, "status_text": "unavailable", "player_name": "Aud Love", "tenniscores_player_id": "nndz-WkM2eHhybndoZz09", "series_id": 3913, "notes": "", "was_new_record": true}	2025-06-22 07:01:20.798988-05
66d1f066-063f-424a-8eac-f4b8982b3918	312236	\N	77	login	User Jessica Freedman logged in successfully	\N	\N	\N	\N	{"associated_players_count": 1, "has_primary_player": true, "primary_player_club": "Tennaqua", "primary_player_series": "Division 16"}	2025-06-22 07:38:05.053713-05
54b0c89b-c94a-4df5-a544-121b2a31acbc	311578	\N	76	login	User Lisa Wagner logged in successfully	\N	\N	\N	\N	{"associated_players_count": 1, "has_primary_player": true, "primary_player_club": "Tennaqua", "primary_player_series": "Division 12"}	2025-06-22 07:39:12.056569-05
993691c3-c12f-4be8-baf8-3d0fd5443ba2	316950	\N	43	login	User Ross Freedman logged in successfully	\N	\N	\N	\N	{"associated_players_count": 2, "has_primary_player": true, "primary_player_club": "Tennaqua", "primary_player_series": "Chicago 22"}	2025-06-22 11:37:30.92946-05
61e52089-904b-4b99-98ff-9ef8ad3e4619	316950	\N	43	login	User Ross Freedman logged in successfully	\N	\N	\N	\N	{"associated_players_count": 2, "has_primary_player": true, "primary_player_club": "Tennaqua", "primary_player_series": "Chicago 22"}	2025-06-22 12:16:16.921372-05
f6645a5b-ccab-4a86-81e8-c62029389cd5	314057	\N	161	user_registration	New user Brian Fox registered successfully	\N	\N	\N	\N	{"association_result": "associated", "association_detail": "Player association created with exact match and team assignment verified", "provided_league": "APTA_CHICAGO", "provided_club": "Tennaqua", "provided_series": "Chicago 7", "player_auto_linked": true, "team_auto_assigned": true}	2025-06-22 13:05:47.201527-05
a666ef6e-b4d6-4198-b7d3-698655e8f3c7	316950	\N	43	login	User Ross Freedman logged in successfully	\N	\N	\N	\N	{"associated_players_count": 2, "has_primary_player": true, "primary_player_club": "Tennaqua", "primary_player_series": "Chicago 22"}	2025-06-22 13:14:46.2825-05
ee2b2bb4-b665-4bfa-9e34-17c4ae7ff5cb	314057	\N	161	login	User Brian Fox logged in successfully	\N	\N	\N	\N	{"associated_players_count": 1, "has_primary_player": true, "primary_player_club": "Tennaqua", "primary_player_series": "Chicago 7"}	2025-06-22 13:16:03.427156-05
79c75b18-1777-4073-b7eb-59e730c5092c	316950	\N	43	login	User Ross Freedman logged in successfully	\N	\N	\N	\N	{"associated_players_count": 2, "has_primary_player": true, "primary_player_club": "Tennaqua", "primary_player_series": "Chicago 22"}	2025-06-22 16:40:52.330486-05
f73031f7-36ae-43ef-933f-a12069bfe3c3	314057	\N	161	login	User Brian Fox logged in successfully	\N	\N	\N	\N	{"associated_players_count": 1, "has_primary_player": true, "primary_player_club": "Tennaqua", "primary_player_series": "Chicago 7"}	2025-06-22 16:41:41.761013-05
6dbf858e-e4d8-46f9-a090-4cef886e8c80	314057	\N	161	availability_update	Updated availability for 2024-09-24 to available	3891	series	127.0.0.1	Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/137.0.0.0 Safari/537.36	{"match_date": "2024-09-24", "availability_status": 1, "status_text": "available", "player_name": "Brian Fox", "tenniscores_player_id": "nndz-WkNPd3g3citnQT09", "series_id": 3891, "notes": "", "was_new_record": true}	2025-06-22 17:00:43.555964-05
34fa871a-115f-49aa-a691-4bc1d31dce76	316950	\N	43	login	User Ross Freedman logged in successfully	\N	\N	\N	\N	{"associated_players_count": 2, "has_primary_player": true, "primary_player_club": "Tennaqua", "primary_player_series": "Chicago 22"}	2025-06-22 17:20:23.2858-05
149a9963-63c8-42f7-933f-8d093da2859e	314057	\N	161	login	User Brian Fox logged in successfully	\N	\N	\N	\N	{"associated_players_count": 1, "has_primary_player": true, "primary_player_club": "Tennaqua", "primary_player_series": "Chicago 7"}	2025-06-22 17:21:24.898129-05
534a1c7d-19aa-4506-b363-f68a137d7436	316950	\N	43	login	User Ross Freedman logged in successfully	\N	\N	\N	\N	{"associated_players_count": 2, "has_primary_player": true, "primary_player_club": "Tennaqua", "primary_player_series": "Chicago 22"}	2025-06-22 18:24:01.993942-05
a1ff6a28-12a8-4c40-9acb-efef763269d6	316950	\N	43	login	User Ross Freedman logged in successfully	\N	\N	\N	\N	{"associated_players_count": 2, "has_primary_player": true, "primary_player_club": "Tennaqua", "primary_player_series": "Chicago 22"}	2025-06-22 20:21:03.432002-05
a57c852b-0f4b-4a25-bbbb-4ea195664eb2	316950	\N	43	login	User Ross Freedman logged in successfully	\N	\N	\N	\N	{"associated_players_count": 2, "has_primary_player": true, "primary_player_club": "Tennaqua", "primary_player_series": "Chicago 22"}	2025-06-22 21:20:36.503382-05
353e093f-f238-497a-9fa2-aa2ef0ca1cc1	316950	\N	43	login	User Ross Freedman logged in successfully	\N	\N	\N	\N	{"associated_players_count": 2, "has_primary_player": true, "primary_player_club": "Tennaqua", "primary_player_series": "Chicago 22"}	2025-06-22 21:30:13.210958-05
652d34d0-4673-4863-8aaf-99a8376a7c55	316950	\N	43	login	User Ross Freedman logged in successfully	\N	\N	\N	\N	{"associated_players_count": 2, "has_primary_player": true, "primary_player_club": "Tennaqua", "primary_player_series": "Chicago 22"}	2025-06-23 17:11:09.018625-05
6e41dcaf-8813-4398-8769-a0f84b8b9caf	316950	\N	43	login	User Ross Freedman logged in successfully	\N	\N	\N	\N	{"associated_players_count": 2, "has_primary_player": true, "primary_player_club": "Tennaqua", "primary_player_series": "Chicago 22"}	2025-06-23 21:52:11.852775-05
cde5e366-7957-4832-890c-b580b21608f2	315456	\N	403	user_registration	New user RRR Jarol registered successfully	\N	\N	\N	\N	{"association_result": "associated", "association_detail": "Player association created with exact match and team assignment verified", "provided_league": "APTA_CHICAGO", "provided_club": "Tennaqua", "provided_series": "Chicago 1", "player_auto_linked": true, "team_auto_assigned": true}	2025-06-23 22:32:07.122163-05
c53e31e0-91d4-4a37-80c0-604ff6bef4e7	316953	\N	49	login	User Victor Forman logged in successfully	\N	\N	\N	\N	{"associated_players_count": 1, "has_primary_player": true, "primary_player_club": "Tennaqua", "primary_player_series": "Chicago 22"}	2025-06-24 09:39:19.097234-05
0f3eb3d0-dd5a-4912-a2d3-ad332c00ccab	\N	\N	43	page_visit	Visited Admin Activity Dashboard page	\N	\N	127.0.0.1	Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/137.0.0.0 Safari/537.36	{"page": "admin_dashboard", "page_category": "admin", "details": "Admin accessed activity monitoring dashboard"}	2025-06-23 18:03:36.570282-05
b2ec06b4-1a7e-45f5-8a04-3729469485ce	316950	\N	43	login	User Ross Freedman logged in successfully	\N	\N	\N	\N	{"associated_players_count": 2, "has_primary_player": true, "primary_player_club": "Tennaqua", "primary_player_series": "Chicago 22"}	2025-06-23 21:26:49.200218-05
1f466419-0930-47a0-93e6-17dd88a0e74e	315456	\N	403	login	User Ryan Jarol logged in successfully	\N	\N	\N	\N	{"associated_players_count": 1, "has_primary_player": true, "primary_player_club": "Tennaqua", "primary_player_series": "Chicago 15"}	2025-06-23 22:33:10.246762-05
4b64b387-726f-449d-8907-c4c19c24da3e	316950	\N	43	login	User Ross Freedman logged in successfully	\N	\N	\N	\N	{"associated_players_count": 2, "has_primary_player": true, "primary_player_club": "Tennaqua", "primary_player_series": "Chicago 22"}	2025-06-24 09:55:06.977716-05
9736d935-313d-47d1-826f-db8e54c4d758	312877	\N	350	login	User Rob Werman logged in successfully	\N	\N	\N	\N	{"associated_players_count": 2, "has_primary_player": true, "primary_player_club": "Tennaqua", "primary_player_series": "Series 2A"}	2025-06-23 18:08:00.914655-05
f5e7bf7c-57d9-42b4-bbe1-a309f8abaa07	316950	\N	43	availability_update	Updated availability for 2024-09-24 to unavailable	3854	series	127.0.0.1	Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/137.0.0.0 Safari/537.36	{"match_date": "2024-09-24", "availability_status": 2, "status_text": "unavailable", "player_name": "Ross Freedman", "tenniscores_player_id": "nndz-WkMrK3didjlnUT09", "series_id": 3854, "notes": "", "was_new_record": false}	2025-06-23 21:27:31.455825-05
33e2d635-7b0b-493e-99f0-ba1d7cc4243f	316226	\N	399	user_registration	New user ggg Swender registered successfully	\N	\N	\N	\N	{"association_result": "associated", "association_detail": "Player association created with exact match and team assignment verified", "provided_league": "APTA_CHICAGO", "provided_club": "Tennaqua", "provided_series": "Chicago 19", "player_auto_linked": true, "team_auto_assigned": true}	2025-06-23 22:01:16.990265-05
39f31938-3cf0-4a40-af9a-bbc65f150016	316950	\N	43	login	User Ross Freedman logged in successfully	\N	\N	\N	\N	{"associated_players_count": 2, "has_primary_player": true, "primary_player_club": "Tennaqua", "primary_player_series": "Chicago 22"}	2025-06-24 06:30:06.442134-05
84bcb3a9-e209-4782-84aa-44e32a1a5217	316953	\N	49	availability_update	Updated availability for 2024-09-24 to unavailable	3854	series	127.0.0.1	Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/137.0.0.0 Safari/537.36	{"match_date": "2024-09-24", "availability_status": 2, "status_text": "unavailable", "player_name": "Victor Forman", "tenniscores_player_id": "nndz-WkMrK3diZjZoZz09", "series_id": 3854, "notes": "", "was_new_record": true}	2025-06-24 09:56:26.412001-05
a86942dc-9cd1-407c-bac9-c25d6ac89a91	316950	\N	43	login	User Ross Freedman logged in successfully	\N	\N	\N	\N	{"associated_players_count": 2, "has_primary_player": true, "primary_player_club": "Tennaqua", "primary_player_series": "Chicago 22"}	2025-06-23 20:58:18.127589-05
2abca24e-32f4-4eb9-894a-5b27bf6694fe	316950	\N	43	availability_update	Updated availability for 2024-09-24 to available	3854	series	127.0.0.1	Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/137.0.0.0 Safari/537.36	{"match_date": "2024-09-24", "availability_status": 1, "status_text": "available", "player_name": "Ross Freedman", "tenniscores_player_id": "nndz-WkMrK3didjlnUT09", "series_id": 3854, "notes": "", "was_new_record": false}	2025-06-23 21:27:32.45528-05
9adaf3f7-0488-4ab6-b345-88666ddd1abb	\N	\N	356	user_registration	New user Gregori Swender registered successfully	\N	\N	\N	\N	{"association_result": "probable_matches_available", "association_detail": "Probable player matches found but skipped auto-association - user can link manually", "provided_league": "APTA_CHICAGO", "provided_club": "Tennaqua", "provided_series": "Chicago 19", "player_auto_linked": false, "team_auto_assigned": false}	2025-06-23 21:35:37.932194-05
33d51744-2e8d-4159-af2f-ac7798c8109e	316950	\N	43	login	User Ross Freedman logged in successfully	\N	\N	\N	\N	{"associated_players_count": 2, "has_primary_player": true, "primary_player_club": "Tennaqua", "primary_player_series": "Chicago 22"}	2025-06-23 15:30:24.067247-05
cffa68a2-92a9-4b36-a2c3-e80c82430936	316952	\N	349	user_registration	New user Howard Dakoff registered successfully	\N	\N	\N	\N	{"association_result": "associated", "association_detail": "Player association created with exact match and team assignment verified", "provided_league": "APTA_CHICAGO", "provided_club": "Tennaqua", "provided_series": "Chicago 22", "player_auto_linked": true, "team_auto_assigned": true}	2025-06-23 16:00:49.880997-05
d7ec2bdd-4915-4926-b728-ef7bf3ef97c5	312877	\N	350	login	User Rob Werman logged in successfully	\N	\N	\N	\N	{"associated_players_count": 2, "has_primary_player": true, "primary_player_club": "Tennaqua", "primary_player_series": "Series 2A"}	2025-06-23 21:00:36.681672-05
9272ab84-b72c-4d41-84d7-3364de55e28a	316217	\N	352	user_registration	New user Dave Arenberg registered successfully	\N	\N	\N	\N	{"association_result": "associated", "association_detail": "Player association created with exact match and team assignment verified", "provided_league": "APTA_CHICAGO", "provided_club": "Tennaqua", "provided_series": "Chicago 19 SW", "player_auto_linked": true, "team_auto_assigned": true}	2025-06-23 21:30:47.075254-05
0d79b171-3dc7-4c20-8f58-f93e81562e5b	316950	\N	43	availability_update	Updated availability for 2024-09-24 to available	3854	series	127.0.0.1	Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/137.0.0.0 Safari/537.36	{"match_date": "2024-09-24", "availability_status": 1, "status_text": "available", "player_name": "Ross Freedman", "tenniscores_player_id": "nndz-WkMrK3didjlnUT09", "series_id": 3854, "notes": "", "was_new_record": true}	2025-06-23 15:30:26.97084-05
19ad69a8-e0fb-4c29-871e-783282f99c91	316950	\N	43	login	User Ross Freedman logged in successfully	\N	\N	\N	\N	{"associated_players_count": 2, "has_primary_player": true, "primary_player_club": "Tennaqua", "primary_player_series": "Chicago 22"}	2025-06-23 21:39:19.128488-05
d0a84b6f-1e5b-4d38-bae3-e803f068fdc8	316950	\N	43	login	User Ross Freedman logged in successfully	\N	\N	\N	\N	{"associated_players_count": 2, "has_primary_player": true, "primary_player_club": "Tennaqua", "primary_player_series": "Chicago 22"}	2025-06-23 22:02:09.700074-05
41739b4a-75da-4da1-81ff-c305b8658a38	316950	\N	43	login	User Ross Freedman logged in successfully	\N	\N	\N	\N	{"associated_players_count": 2, "has_primary_player": true, "primary_player_club": "Tennaqua", "primary_player_series": "Chicago 22"}	2025-06-24 07:02:12.682468-05
3dce419b-26d2-47e7-b61b-9412a0cf3854	316953	\N	49	availability_update	Updated availability for 2024-09-24 to unavailable	3854	series	127.0.0.1	Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/137.0.0.0 Safari/537.36	{"match_date": "2024-09-24", "availability_status": 2, "status_text": "unavailable", "player_name": "Victor Forman", "tenniscores_player_id": "nndz-WkMrK3diZjZoZz09", "series_id": 3854, "notes": "Will be late", "was_new_record": false}	2025-06-24 09:56:32.509906-05
25b1b36b-062b-4af1-8e24-c54150027cb2	316950	\N	43	availability_update	Updated availability for 2024-09-24 to available	3854	series	127.0.0.1	Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/137.0.0.0 Safari/537.36	{"match_date": "2024-09-24", "availability_status": 1, "status_text": "available", "player_name": "Ross Freedman", "tenniscores_player_id": "nndz-WkMrK3didjlnUT09", "series_id": 3854, "notes": "Will be there", "was_new_record": false}	2025-06-23 15:30:45.106338-05
9a90ea17-f2a3-4a5c-adb9-c42523add05c	314065	\N	350	user_registration	New user Rob Werman registered successfully	\N	\N	\N	\N	{"association_result": "associated", "association_detail": "Player association created with exact match and team assignment verified", "provided_league": "APTA_CHICAGO", "provided_club": "Tennaqua", "provided_series": "Chicago 7", "player_auto_linked": true, "team_auto_assigned": true}	2025-06-23 16:47:23.191596-05
1853231d-294f-415c-8bad-daed90d10681	313005	\N	43	login	User Ross Freedman logged in successfully	\N	\N	\N	\N	{"associated_players_count": 2, "has_primary_player": true, "primary_player_club": "Tennaqua", "primary_player_series": "Series 2B"}	2025-06-23 21:13:14.235788-05
dde29012-e69e-4e5e-8f54-03d852371d34	316950	\N	43	login	User Ross Freedman logged in successfully	\N	\N	\N	\N	{"associated_players_count": 2, "has_primary_player": true, "primary_player_club": "Tennaqua", "primary_player_series": "Chicago 22"}	2025-06-23 21:31:20.084549-05
0a058ac6-490b-4f49-bea8-9ce21565aaf5	316950	\N	43	login	User Ross Freedman logged in successfully	\N	\N	\N	\N	{"associated_players_count": 2, "has_primary_player": true, "primary_player_club": "Tennaqua", "primary_player_series": "Chicago 22"}	2025-06-24 10:32:42.655102-05
2b800a45-991d-4814-b61f-4f996085e538	\N	\N	357	user_registration	New user G Swender registered successfully	\N	\N	\N	\N	{"association_result": "probable_matches_available", "association_detail": "Probable player matches found but skipped auto-association - user can link manually", "provided_league": "APTA_CHICAGO", "provided_club": "Tennaqua", "provided_series": "Chicago 19", "player_auto_linked": false, "team_auto_assigned": false}	2025-06-23 21:40:17.893834-05
66b7c06b-79ec-46e3-a68f-11299f0dfdc7	316950	\N	43	login	User Ross Freedman logged in successfully	\N	\N	\N	\N	{"associated_players_count": 2, "has_primary_player": true, "primary_player_club": "Tennaqua", "primary_player_series": "Chicago 22"}	2025-06-23 22:30:49.760481-05
5c68e124-fbea-4554-941d-3617ba220b51	309808	\N	404	user_registration	New user Olga Martinsone registered successfully	\N	\N	\N	\N	{"association_result": "associated", "association_detail": "Player association created with exact match and team assignment verified", "provided_league": "CNSWPL", "provided_club": "LifeSport", "provided_series": "Division 1", "player_auto_linked": true, "team_auto_assigned": true}	2025-06-24 07:10:37.568036-05
74488735-db4a-4441-85c6-982d2395087b	316950	\N	43	login	User Ross Freedman logged in successfully	\N	\N	\N	\N	{"associated_players_count": 2, "has_primary_player": true, "primary_player_club": "Tennaqua", "primary_player_series": "Chicago 22"}	2025-06-24 15:53:17.574404-05
bd5a2af9-4bf6-4dc6-ad40-b66046d9c527	316216	\N	409	user_registration	New user P Katai registered successfully	\N	\N	\N	\N	{"association_result": "associated", "association_detail": "Player association created with exact match and team assignment verified", "provided_league": "APTA_CHICAGO", "provided_club": "Tennaqua", "provided_series": "Chicago 19", "player_auto_linked": true, "team_auto_assigned": true}	2025-06-24 15:54:02.789592-05
4314bf48-8fb4-41e2-a0e4-6497b235f09e	316950	\N	43	login	User Ross Freedman logged in successfully	\N	\N	\N	\N	{"associated_players_count": 2, "has_primary_player": true, "primary_player_club": "Tennaqua", "primary_player_series": "Chicago 22"}	2025-06-24 18:10:29.059094-05
e16f009c-e632-45ff-87cf-6f3ccd015001	316953	\N	49	login	User Victor Forman logged in successfully	\N	\N	\N	\N	{"associated_players_count": 1, "has_primary_player": true, "primary_player_club": "Tennaqua", "primary_player_series": "Chicago 22"}	2025-06-24 18:26:17.726714-05
8acaec04-0695-4502-89da-d80bbf88c5b2	\N	\N	49	login	User Victor Forman logged in successfully	\N	\N	\N	\N	{"associated_players_count": 0, "has_primary_player": false, "primary_player_club": null, "primary_player_series": null}	2025-06-24 19:45:22.096965-05
\.


--
-- TOC entry 4132 (class 0 OID 46448)
-- Dependencies: 217
-- Data for Name: alembic_version; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.alembic_version (version_num) FROM stdin;
5b40b3419ab4
\.


--
-- TOC entry 4133 (class 0 OID 46451)
-- Dependencies: 218
-- Data for Name: club_leagues; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.club_leagues (id, club_id, league_id, created_at) FROM stdin;
79380	4623	4514	2025-06-24 19:48:53.482553-05
79381	4586	4511	2025-06-24 19:48:53.482553-05
79382	4604	4511	2025-06-24 19:48:53.482553-05
79383	4643	4511	2025-06-24 19:48:53.482553-05
79384	4602	4511	2025-06-24 19:48:53.482553-05
79385	4632	4511	2025-06-24 19:48:53.482553-05
79386	4644	4511	2025-06-24 19:48:53.482553-05
79387	4645	4511	2025-06-24 19:48:53.482553-05
79388	4587	4511	2025-06-24 19:48:53.482553-05
79389	4588	4511	2025-06-24 19:48:53.482553-05
79390	4630	4511	2025-06-24 19:48:53.482553-05
79391	4626	4511	2025-06-24 19:48:53.482553-05
79392	4636	4511	2025-06-24 19:48:53.482553-05
79393	4573	4511	2025-06-24 19:48:53.482553-05
79394	4647	4511	2025-06-24 19:48:53.482553-05
79395	4648	4511	2025-06-24 19:48:53.482553-05
79396	4578	4511	2025-06-24 19:48:53.482553-05
79397	4596	4511	2025-06-24 19:48:53.482553-05
79398	4619	4511	2025-06-24 19:48:53.482553-05
79399	4591	4511	2025-06-24 19:48:53.482553-05
79400	4592	4511	2025-06-24 19:48:53.482553-05
79401	4605	4511	2025-06-24 19:48:53.482553-05
79402	4613	4511	2025-06-24 19:48:53.482553-05
79403	4568	4511	2025-06-24 19:48:53.482553-05
79404	4576	4511	2025-06-24 19:48:53.482553-05
79405	4582	4511	2025-06-24 19:48:53.482553-05
79406	4597	4511	2025-06-24 19:48:53.482553-05
79407	4598	4511	2025-06-24 19:48:53.482553-05
79408	4627	4511	2025-06-24 19:48:53.482553-05
79409	4628	4511	2025-06-24 19:48:53.482553-05
79410	4594	4511	2025-06-24 19:48:53.482553-05
79411	4621	4511	2025-06-24 19:48:53.482553-05
79412	4622	4511	2025-06-24 19:48:53.482553-05
79413	4577	4511	2025-06-24 19:48:53.482553-05
79414	4641	4511	2025-06-24 19:48:53.482553-05
79415	4609	4511	2025-06-24 19:48:53.482553-05
79416	4570	4511	2025-06-24 19:48:53.482553-05
79417	4606	4511	2025-06-24 19:48:53.482553-05
79418	4607	4511	2025-06-24 19:48:53.482553-05
79419	4625	4511	2025-06-24 19:48:53.482553-05
79420	4583	4511	2025-06-24 19:48:53.482553-05
79421	4584	4511	2025-06-24 19:48:53.482553-05
79422	4633	4511	2025-06-24 19:48:53.482553-05
79423	4634	4511	2025-06-24 19:48:53.482553-05
79424	4614	4511	2025-06-24 19:48:53.482553-05
79425	4615	4511	2025-06-24 19:48:53.482553-05
79426	4629	4511	2025-06-24 19:48:53.482553-05
79427	4567	4511	2025-06-24 19:49:47.820533-05
79429	4569	4511	2025-06-24 19:49:47.821854-05
79434	4574	4511	2025-06-24 19:49:47.822573-05
79449	4589	4511	2025-06-24 19:49:47.82405-05
79463	4603	4511	2025-06-24 19:49:47.825611-05
79476	4616	4511	2025-06-24 19:49:47.826909-05
79478	4618	4511	2025-06-24 19:49:47.827237-05
79483	4623	4511	2025-06-24 19:49:47.827791-05
79484	4624	4511	2025-06-24 19:49:47.827994-05
79502	4642	4511	2025-06-24 19:49:47.829686-05
79307	4571	4514	2025-06-24 19:48:53.482553-05
79308	4571	4511	2025-06-24 19:48:53.482553-05
79309	4571	4513	2025-06-24 19:48:53.482553-05
79310	4590	4511	2025-06-24 19:48:53.482553-05
79311	4590	4513	2025-06-24 19:48:53.482553-05
79312	4599	4511	2025-06-24 19:48:53.482553-05
79313	4599	4513	2025-06-24 19:48:53.482553-05
79314	4603	4513	2025-06-24 19:48:53.482553-05
79315	4608	4511	2025-06-24 19:48:53.482553-05
79316	4608	4513	2025-06-24 19:48:53.482553-05
79317	4610	4514	2025-06-24 19:48:53.482553-05
79318	4610	4511	2025-06-24 19:48:53.482553-05
79319	4610	4513	2025-06-24 19:48:53.482553-05
79320	4631	4511	2025-06-24 19:48:53.482553-05
79321	4631	4513	2025-06-24 19:48:53.482553-05
79322	4637	4511	2025-06-24 19:48:53.482553-05
79323	4637	4513	2025-06-24 19:48:53.482553-05
79324	4646	4514	2025-06-24 19:48:53.482553-05
79325	4646	4511	2025-06-24 19:48:53.482553-05
79326	4646	4513	2025-06-24 19:48:53.482553-05
79327	4579	4511	2025-06-24 19:48:53.482553-05
79328	4579	4513	2025-06-24 19:48:53.482553-05
79329	4593	4511	2025-06-24 19:48:53.482553-05
79330	4593	4513	2025-06-24 19:48:53.482553-05
79331	4601	4511	2025-06-24 19:48:53.482553-05
79332	4601	4513	2025-06-24 19:48:53.482553-05
79333	4611	4511	2025-06-24 19:48:53.482553-05
79334	4611	4513	2025-06-24 19:48:53.482553-05
79335	4612	4514	2025-06-24 19:48:53.482553-05
79336	4612	4511	2025-06-24 19:48:53.482553-05
79337	4612	4513	2025-06-24 19:48:53.482553-05
79338	4620	4511	2025-06-24 19:48:53.482553-05
79339	4620	4513	2025-06-24 19:48:53.482553-05
79340	4635	4514	2025-06-24 19:48:53.482553-05
79341	4635	4511	2025-06-24 19:48:53.482553-05
79342	4635	4513	2025-06-24 19:48:53.482553-05
79343	4639	4514	2025-06-24 19:48:53.482553-05
79344	4639	4511	2025-06-24 19:48:53.482553-05
79345	4639	4513	2025-06-24 19:48:53.482553-05
79346	4575	4511	2025-06-24 19:48:53.482553-05
79347	4575	4513	2025-06-24 19:48:53.482553-05
79348	4585	4511	2025-06-24 19:48:53.482553-05
79349	4585	4513	2025-06-24 19:48:53.482553-05
79350	4617	4511	2025-06-24 19:48:53.482553-05
79351	4617	4513	2025-06-24 19:48:53.482553-05
79352	4638	4514	2025-06-24 19:48:53.482553-05
79353	4638	4511	2025-06-24 19:48:53.482553-05
79354	4638	4513	2025-06-24 19:48:53.482553-05
79355	4640	4511	2025-06-24 19:48:53.482553-05
79356	4640	4513	2025-06-24 19:48:53.482553-05
79357	4642	4514	2025-06-24 19:48:53.482553-05
79358	4642	4513	2025-06-24 19:48:53.482553-05
79359	4580	4514	2025-06-24 19:48:53.482553-05
79360	4580	4511	2025-06-24 19:48:53.482553-05
79361	4580	4513	2025-06-24 19:48:53.482553-05
79362	4581	4511	2025-06-24 19:48:53.482553-05
79363	4581	4513	2025-06-24 19:48:53.482553-05
79364	4618	4513	2025-06-24 19:48:53.482553-05
79365	4624	4513	2025-06-24 19:48:53.482553-05
79366	4589	4513	2025-06-24 19:48:53.482553-05
79367	4595	4511	2025-06-24 19:48:53.482553-05
79368	4595	4513	2025-06-24 19:48:53.482553-05
79369	4600	4514	2025-06-24 19:48:53.482553-05
79370	4600	4511	2025-06-24 19:48:53.482553-05
79371	4600	4513	2025-06-24 19:48:53.482553-05
79372	4572	4511	2025-06-24 19:48:53.482553-05
79373	4572	4513	2025-06-24 19:48:53.482553-05
79374	4649	4511	2025-06-24 19:48:53.482553-05
79375	4649	4513	2025-06-24 19:48:53.482553-05
79376	4569	4513	2025-06-24 19:48:53.482553-05
79377	4567	4513	2025-06-24 19:48:53.482553-05
79378	4574	4513	2025-06-24 19:48:53.482553-05
79379	4616	4514	2025-06-24 19:48:53.482553-05
\.


--
-- TOC entry 4135 (class 0 OID 46456)
-- Dependencies: 220
-- Data for Name: clubs; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.clubs (id, name, updated_at, club_address) FROM stdin;
4567	Barrington Hills	2025-06-24 19:48:53.448685-05	\N
4568	Barrington Hills CC	2025-06-24 19:48:53.448685-05	\N
4569	Biltmore	2025-06-24 19:48:53.448685-05	\N
4570	Biltmore CC	2025-06-24 19:48:53.448685-05	\N
4571	Birchwood	2025-06-24 19:48:53.448685-05	\N
4572	Briarwood	2025-06-24 19:48:53.448685-05	\N
4573	Bryn Mawr	2025-06-24 19:48:53.448685-05	\N
4574	Bryn Mawr CC	2025-06-24 19:48:53.448685-05	\N
4575	Butterfield	2025-06-24 19:48:53.448685-05	\N
4576	Chicago Highlands	2025-06-24 19:48:53.448685-05	\N
4577	Dunham Woods	2025-06-24 19:48:53.448685-05	\N
4578	Edgewood Valley	2025-06-24 19:48:53.448685-05	\N
4579	Evanston	2025-06-24 19:48:53.448685-05	\N
4580	Exmoor	2025-06-24 19:48:53.448685-05	\N
4581	Glen Ellyn	2025-06-24 19:48:53.448685-05	\N
4582	Glen Oak	2025-06-24 19:48:53.448685-05	\N
4583	Glen Oak I	2025-06-24 19:48:53.448685-05	\N
4584	Glen Oak II	2025-06-24 19:48:53.448685-05	\N
4585	Glen View	2025-06-24 19:48:53.448685-05	\N
4586	Glenbrook RC	2025-06-24 19:48:53.448685-05	\N
4587	Hawthorn Woods	2025-06-24 19:48:53.448685-05	\N
4588	Hinsdale GC	2025-06-24 19:48:53.448685-05	\N
4589	Hinsdale Golf Club	2025-06-24 19:48:53.448685-05	\N
4590	Hinsdale PC	2025-06-24 19:48:53.448685-05	\N
4591	Hinsdale PC I	2025-06-24 19:48:53.448685-05	\N
4592	Hinsdale PC II	2025-06-24 19:48:53.448685-05	\N
4593	Indian Hill	2025-06-24 19:48:53.448685-05	\N
4594	Inverness	2025-06-24 19:48:53.448685-05	\N
4595	Knollwood	2025-06-24 19:48:53.448685-05	\N
4596	LaGrange CC	2025-06-24 19:48:53.448685-05	\N
4597	LaGrange CC I	2025-06-24 19:48:53.448685-05	\N
4598	LaGrange CC II	2025-06-24 19:48:53.448685-05	\N
4599	Lake Bluff	2025-06-24 19:48:53.448685-05	\N
4600	Lake Forest	2025-06-24 19:48:53.448685-05	\N
4601	Lake Shore CC	2025-06-24 19:48:53.448685-05	\N
4602	Lakeshore S&F	2025-06-24 19:48:53.448685-05	\N
4603	LifeSport	2025-06-24 19:48:53.448685-05	\N
4604	Lifesport-Lshire	2025-06-24 19:48:53.448685-05	\N
4605	Medinah	2025-06-24 19:48:53.448685-05	\N
4606	Medinah I	2025-06-24 19:48:53.448685-05	\N
4607	Medinah II	2025-06-24 19:48:53.448685-05	\N
4608	Michigan Shores	2025-06-24 19:48:53.448685-05	\N
4609	Midt-Bannockburn	2025-06-24 19:48:53.448685-05	\N
4610	Midtown	2025-06-24 19:48:53.448685-05	\N
4611	North Shore	2025-06-24 19:48:53.448685-05	\N
4612	Northmoor	2025-06-24 19:48:53.448685-05	\N
4613	Oak Park CC	2025-06-24 19:48:53.448685-05	\N
4614	Oak Park CC I	2025-06-24 19:48:53.448685-05	\N
4615	Oak Park CC II	2025-06-24 19:48:53.448685-05	\N
4616	Old Willow	2025-06-24 19:48:53.448685-05	\N
4617	Onwentsia	2025-06-24 19:48:53.448685-05	\N
4618	Park Ridge	2025-06-24 19:48:53.448685-05	\N
4619	Park Ridge CC	2025-06-24 19:48:53.448685-05	\N
4620	Prairie Club	2025-06-24 19:48:53.448685-05	\N
4621	Prairie Club I	2025-06-24 19:48:53.448685-05	\N
4622	Prairie Club II	2025-06-24 19:48:53.448685-05	\N
4623	Ravinia Green	2025-06-24 19:48:53.448685-05	\N
4624	River Forest	2025-06-24 19:48:53.448685-05	\N
4625	River Forest CC	2025-06-24 19:48:53.448685-05	\N
4626	River Forest PD	2025-06-24 19:48:53.448685-05	\N
4627	River Forest PD I	2025-06-24 19:48:53.448685-05	\N
4628	River Forest PD II	2025-06-24 19:48:53.448685-05	\N
4629	Royal Melbourne	2025-06-24 19:48:53.448685-05	\N
4630	Ruth Lake	2025-06-24 19:48:53.448685-05	\N
4631	Saddle & Cycle	2025-06-24 19:48:53.448685-05	\N
4632	Salt Creek	2025-06-24 19:48:53.448685-05	\N
4633	Salt Creek I	2025-06-24 19:48:53.448685-05	\N
4634	Salt Creek II	2025-06-24 19:48:53.448685-05	\N
4635	Skokie	2025-06-24 19:48:53.448685-05	\N
4636	South Barrington	2025-06-24 19:48:53.448685-05	\N
4637	Sunset Ridge	2025-06-24 19:48:53.448685-05	\N
4638	Tennaqua	2025-06-24 19:48:53.448685-05	\N
4639	Valley Lo	2025-06-24 19:48:53.448685-05	\N
4640	Westmoreland	2025-06-24 19:48:53.448685-05	\N
4641	White Eagle	2025-06-24 19:48:53.448685-05	\N
4642	Wilmette	2025-06-24 19:48:53.448685-05	\N
4643	Wilmette PD	2025-06-24 19:48:53.448685-05	\N
4644	Wilmette PD I	2025-06-24 19:48:53.448685-05	\N
4645	Wilmette PD II	2025-06-24 19:48:53.448685-05	\N
4646	Winnetka	2025-06-24 19:48:53.448685-05	\N
4647	Winnetka I	2025-06-24 19:48:53.448685-05	\N
4648	Winnetka II	2025-06-24 19:48:53.448685-05	\N
4649	Winter Club	2025-06-24 19:48:53.448685-05	\N
\.


--
-- TOC entry 4137 (class 0 OID 46463)
-- Dependencies: 222
-- Data for Name: leagues; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.leagues (id, league_id, league_name, league_url, created_at, updated_at) FROM stdin;
4511	APTA_CHICAGO	APTA Chicago	https://aptachicago.tenniscores.com/	2025-06-24 19:48:53.446037-05	2025-06-24 19:48:53.446037-05
4512	CITA	CITA		2025-06-24 19:48:53.446037-05	2025-06-24 19:48:53.446037-05
4513	CNSWPL	Chicago North Shore Women's Platform Tennis League	https://cnswpl.tenniscores.com/	2025-06-24 19:48:53.446037-05	2025-06-24 19:48:53.446037-05
4514	NSTF	North Shore Tennis Foundation	https://nstf.org/	2025-06-24 19:48:53.446037-05	2025-06-24 19:48:53.446037-05
4516	APTA_NATIONAL	APTA National	https://apta.tenniscores.com/	2025-06-24 19:49:47.81857-05	2025-06-24 19:49:47.81857-05
\.


--
-- TOC entry 4139 (class 0 OID 46471)
-- Dependencies: 224
-- Data for Name: match_scores; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.match_scores (id, match_date, home_team, away_team, home_player_1_id, home_player_2_id, away_player_1_id, away_player_2_id, scores, winner, created_at, league_id, home_team_id, away_team_id) FROM stdin;
\.


--
-- TOC entry 4144 (class 0 OID 46511)
-- Dependencies: 230
-- Data for Name: player_availability; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.player_availability (id, player_name, availability_status, updated_at, series_id, match_date, player_id, notes) FROM stdin;
165	Ross Freedman	1	2025-06-19 09:04:41.196304-05	1203	2024-10-28 19:00:00-05	103664	test
161	Scott Osterman	3	2025-06-19 09:25:45.111867-05	1224	2024-11-06 18:00:00-06	106616	I'll be there!!!!!
157	Scott Osterman	1	2025-06-19 09:26:11.070028-05	1224	2024-09-25 19:00:00-05	106616	Count me in!
159	Scott Osterman	3	2025-06-19 07:33:16.784676-05	1224	2024-10-16 19:00:00-05	106616	May be 10 minutes late
160	Scott Osterman	3	2025-06-19 07:33:49.347937-05	1224	2024-10-09 19:00:00-05	106616	I really don't know
162	Scott Osterman	3	2025-06-19 07:34:28.310176-05	1224	2024-11-13 18:00:00-06	106616	test
170	Ross Freedman	2	2025-06-19 10:24:11.424641-05	1203	2024-09-23 19:00:00-05	103664	10 min late
171	Ross Freedman	3	2025-06-19 10:26:59.800011-05	1203	2024-09-30 19:00:00-05	103664	Test
172	Ross Freedman	2	2025-06-19 15:05:56.92477-05	1317	2024-09-23 19:00:00-05	118952	Test note
173	Ross Freedman	1	2025-06-19 15:06:37.92331-05	1317	2024-09-30 19:00:00-05	118952	Wedding
174	Ross Freedman	3	2025-06-19 15:06:47.438666-05	1317	2024-10-07 19:00:00-05	118952	Hello
163	Scott Osterman	3	2025-06-19 08:11:24.72016-05	1224	2025-01-08 18:00:00-06	106616	
158	Scott Osterman	3	2025-06-19 08:19:26.476529-05	1224	2024-10-02 19:00:00-05	106616	testttt
164	Scott Osterman	3	2025-06-19 08:25:38.265896-05	1224	2024-11-20 18:00:00-06	106616	i will be there!
175	Ross Freedman	1	2025-06-19 15:26:28.383945-05	1317	2024-12-02 18:00:00-06	118952	
177	Ross Freedman	2	2025-06-19 15:26:31.227769-05	1317	2024-12-09 18:00:00-06	118952	
178	Ross Freedman	3	2025-06-19 15:26:32.804708-05	1317	2024-12-16 18:00:00-06	118952	
179	Ross Freedman	3	2025-06-19 15:26:48.157338-05	1317	2025-01-06 18:00:00-06	118952	Test on 1/7
156	Steve Fretzin	1	2025-06-18 19:06:15.90165-05	1232	2024-09-24 19:00:00-05	101094	\N
180	Ross Freedman	1	2025-06-19 15:32:30.829385-05	1317	2025-09-16 19:00:00-05	118952	Last practice!
181	Rob Werman	1	2025-06-19 15:42:50.237384-05	1350	2025-05-28 19:00:00-05	114879	Test
183	Greg Swender	2	2025-06-20 16:39:47.291138-05	1718	2025-01-06 18:00:00-06	172054	
184	Greg Swender	1	2025-06-20 16:39:49.022568-05	1718	2025-01-13 18:00:00-06	172054	
185	Ross Freedman	2	2025-06-20 17:21:48.397429-05	1724	2024-09-30 19:00:00-05	172778	
182	Ross Freedman	3	2025-06-21 07:07:41.961129-05	1724	2024-09-23 19:00:00-05	172778	
186	Ross Freedman	1	2025-06-21 11:07:48.105065-05	1812	2024-09-23 19:00:00-05	183076	
187	Lisa Wagner	1	2025-06-21 11:12:20.878638-05	1847	2025-01-08 18:00:00-06	177704	
188	Jessica Freedman	1	2025-06-21 17:08:23.487363-05	2733	2025-01-09 18:00:00-06	229852	Test
189	Jessica Freedman	1	2025-06-21 17:42:03.99688-05	3174	2025-01-09 18:00:00-06	281342	
190	Aud Love	2	2025-06-22 07:01:20.770252-05	3913	2025-01-09 18:00:00-06	312245	
191	Brian Fox	1	2025-06-22 12:09:04.863423-05	3891	2024-12-02 18:00:00-06	314057	
192	Brian Fox	1	2025-06-22 17:00:43.543675-05	3891	2024-09-23 19:00:00-05	314057	
193	Ross Freedman	1	2025-06-23 21:27:32.446982-05	3854	2024-09-23 19:00:00-05	316950	
194	Victor Forman	2	2025-06-24 09:56:32.501339-05	3854	2024-09-23 19:00:00-05	316953	Will be late
\.


--
-- TOC entry 4146 (class 0 OID 46521)
-- Dependencies: 232
-- Data for Name: player_history; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.player_history (id, series, date, end_pti, created_at, league_id, player_id) FROM stdin;
\.


--
-- TOC entry 4148 (class 0 OID 46526)
-- Dependencies: 234
-- Data for Name: player_season_tracking; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.player_season_tracking (id, player_id, league_id, season_year, forced_byes, not_available, injury, created_at, updated_at) FROM stdin;
1	nndz-WkM2L3c3djZndz09	4418	2024	1	0	0	2025-06-20 13:21:16.711476-05	2025-06-20 13:26:01.452472-05
3	nndz-WkMrK3dMNzVoQT09	4418	2024	0	1	0	2025-06-20 13:21:57.738495-05	2025-06-20 13:21:59.718502-05
8	nndz-WkMrK3didjlnUT09	4418	2024	0	0	4	2025-06-20 13:26:01.696999-05	2025-06-20 13:26:07.17866-05
19	nndz-WlNlN3dyYnhqUT09	4418	2024	2	3	1	2025-06-20 13:26:45.451748-05	2025-06-20 13:26:48.668037-05
24	nndz-WkNPd3liNzlnQT09	4418	2024	2	2	0	2025-06-20 14:32:41.512723-05	2025-06-20 14:32:50.24138-05
26	nndz-WkNHeHdiZjhoZz09	4418	2024	1	0	0	2025-06-20 14:32:44.915696-05	2025-06-20 14:32:47.14219-05
31	nndz-WkNPd3hydjZoQT09	4418	2024	0	0	3	2025-06-20 14:32:50.483298-05	2025-06-20 14:32:51.145418-05
33	nndz-WkNDd3liZitndz09	4489	2024	0	0	0	2025-06-22 16:58:35.191622-05	2025-06-22 16:58:35.191622-05
35	nndz-WkNHeHdiZjVoUT09	4489	2024	2	0	0	2025-06-22 18:20:38.486002-05	2025-06-22 18:20:38.485872-05
34	nndz-WkM2L3c3djZndz09	4489	2024	2	2	0	2025-06-22 17:20:45.210512-05	2025-06-23 21:19:42.542824-05
39	nndz-WkMrK3dMNzVoQT09	4489	2024	2	2	0	2025-06-23 21:18:49.47124-05	2025-06-23 21:19:44.154876-05
41	nndz-WkMrK3didnhoUT09	4489	2024	2	2	0	2025-06-23 21:18:51.64125-05	2025-06-23 21:19:45.311518-05
43	nndz-WkM2L3c3djZnQT09	4489	2024	2	1	0	2025-06-23 21:18:52.699137-05	2025-06-23 21:19:47.36325-05
66	nndz-WkNDNnhyYjZoZz09	4489	2024	4	0	0	2025-06-23 21:20:01.72829-05	2025-06-23 21:20:04.069889-05
37	nndz-WkMrK3didjlnUT09	4489	2024	2	1	5	2025-06-22 18:28:11.15925-05	2025-06-23 21:20:06.140953-05
72	nndz-WkNHeHdiZjVoZz09	4489	2024	2	4	0	2025-06-23 21:20:11.79161-05	2025-06-23 21:20:14.850664-05
64	nndz-WkMrK3diZjZoZz09	4489	2024	2	2	0	2025-06-23 21:19:54.911829-05	2025-06-23 21:20:17.709187-05
65	nndz-WkM2L3c3bjhoUT09	4489	2024	2	2	1	2025-06-23 21:19:56.654908-05	2025-06-23 21:20:47.019766-05
45	nndz-WkM2L3c3bjlqUT09	4489	2024	1	2	1	2025-06-23 21:18:59.380722-05	2025-06-23 21:20:51.30872-05
\.


--
-- TOC entry 4141 (class 0 OID 46479)
-- Dependencies: 226
-- Data for Name: players; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.players (id, email, first_name, last_name, club_id, series_id, created_at, tenniscores_player_id, league_id, is_active, pti, wins, losses, win_percentage, captain_status, updated_at, career_wins, career_losses, career_matches, career_win_percentage, team_id) FROM stdin;
324326	\N	Sari	Hirsch	4571	4330	2025-06-24 19:48:53.831168-05	nndz-WkNDOHlMNytoZz09	4513	t	\N	17	2	89.50	C	2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
324327	\N	Lisa	Korach	4571	4330	2025-06-24 19:48:53.831168-05	nndz-WkNDOHlMNytodz09	4513	t	\N	17	2	89.50	CC	2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
324328	\N	Samantha	Borstein	4571	4330	2025-06-24 19:48:53.831168-05	nndz-WkNDOHlMM3hndz09	4513	t	\N	6	2	75.00		2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
324329	\N	Debbie	Goldstein	4571	4330	2025-06-24 19:48:53.831168-05	nndz-WkNDOHlMbjVodz09	4513	t	\N	7	2	77.80		2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
324330	\N	Leslie	Katz	4571	4330	2025-06-24 19:48:53.831168-05	nndz-WkM2eHhMYnhodz09	4513	t	\N	16	4	80.00		2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
324331	\N	Susan	Kramer	4571	4330	2025-06-24 19:48:53.831168-05	nndz-WkNDOHlMbjVnUT09	4513	t	\N	7	1	87.50		2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
324332	\N	Alison	Morgan	4571	4330	2025-06-24 19:48:53.831168-05	nndz-WkNDOHlMdjZqUT09	4513	t	\N	43	9	82.70		2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
324333	\N	Jamie	Zaransky	4571	4330	2025-06-24 19:48:53.831168-05	nndz-WkM2eHhMbi9oZz09	4513	t	\N	18	4	81.80		2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
324334	\N	Elizabeth	Fox	4571	4330	2025-06-24 19:48:53.831168-05	nndz-WkNHNXdyejRndz09	4513	t	\N	6	2	75.00		2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
324335	\N	Laura	Isaacson	4571	4330	2025-06-24 19:48:53.831168-05	nndz-WkNDOHlMMytqUT09	4513	t	\N	3	6	33.30		2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
324336	\N	Jody	Rotblatt	4571	4330	2025-06-24 19:48:53.831168-05	nndz-WkM2eHhMZitoQT09	4513	t	\N	0	1	0.00		2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
324337	\N	Svetlana	Schroeder	4590	4344	2025-06-24 19:48:53.831168-05	nndz-WkNDOHlMejVoZz09	4513	t	\N	12	7	63.20	C	2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
324338	\N	Chris	O'Malley	4590	4344	2025-06-24 19:48:53.831168-05	nndz-WkNDOHlMejRnQT09	4513	t	\N	3	2	60.00	CC	2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
324339	\N	Melissa	Burke	4590	4344	2025-06-24 19:48:53.831168-05	nndz-WkM2eHliejhndz09	4513	t	\N	7	3	70.00		2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
324340	\N	Kristen	Evans	4590	4344	2025-06-24 19:48:53.831168-05	nndz-WkNDOHlMejRoUT09	4513	t	\N	8	10	44.40		2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
324341	\N	Nancy	Gaspadarek	4590	4344	2025-06-24 19:48:53.831168-05	nndz-WkNDOHlMejRoQT09	4513	t	\N	13	12	52.00		2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
324342	\N	Ellie	Hay	4590	4344	2025-06-24 19:48:53.831168-05	nndz-WkM2d3c3MzZnZz09	4513	t	\N	15	6	71.40		2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
324343	\N	Courtney	Hughes	4590	4344	2025-06-24 19:48:53.831168-05	nndz-WkNDOHlMbjdndz09	4513	t	\N	4	3	57.10		2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
324344	\N	Maggie	Jessopp	4590	4344	2025-06-24 19:48:53.831168-05	nndz-WkM2eHliei9oQT09	4513	t	\N	8	8	50.00		2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
324345	\N	Christine	Neuman	4590	4344	2025-06-24 19:48:53.831168-05	nndz-WkMrK3lMandqUT09	4513	t	\N	6	4	60.00		2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
324346	\N	Jennifer	Thomas	4590	4344	2025-06-24 19:48:53.831168-05	nndz-WkM2eHhMbi9qQT09	4513	t	\N	7	4	63.60		2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
324347	\N	Stephanie	Turner	4590	4344	2025-06-24 19:48:53.831168-05	nndz-WkNDOHlMbjdnUT09	4513	t	\N	3	3	50.00		2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
324348	\N	Shawna	Zsinko	4590	4344	2025-06-24 19:48:53.831168-05	nndz-WkNDOHlMejVodz09	4513	t	\N	0	0	0.00		2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
324349	\N	Mia	Cleary	4590	4345	2025-06-24 19:48:53.831168-05	nndz-WkM2eHliMzVnUT09	4513	t	\N	5	12	29.40	C	2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
324350	\N	Candace	Allen	4590	4345	2025-06-24 19:48:53.831168-05	nndz-WlNhK3dydi9oZz09	4513	t	\N	0	11	0.00		2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
324351	\N	Sue	Arends	4590	4345	2025-06-24 19:48:53.831168-05	nndz-WkM2eHlMLzVqUT09	4513	t	\N	2	9	18.20		2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
324352	\N	Diane	Colleran	4590	4345	2025-06-24 19:48:53.831168-05	nndz-WkM2eHlienhqUT09	4513	t	\N	3	9	25.00		2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
324353	\N	Jackie	Edgewater	4590	4345	2025-06-24 19:48:53.831168-05	nndz-WkM2eHliejhnZz09	4513	t	\N	1	6	14.30		2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
324354	\N	Kelly	Kenna	4590	4345	2025-06-24 19:48:53.831168-05	nndz-WlNlL3dyZjRnQT09	4513	t	\N	11	13	45.80		2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
324355	\N	Liz	McCleary	4590	4345	2025-06-24 19:48:53.831168-05	nndz-WkM2d3g3ai9qUT09	4513	t	\N	7	14	33.30		2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
324356	\N	Tracy	Milefchik	4590	4345	2025-06-24 19:48:53.831168-05	nndz-WkM2eHliendoQT09	4513	t	\N	1	1	50.00		2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
324357	\N	Alicia	O'Connor	4590	4345	2025-06-24 19:48:53.831168-05	nndz-WkM2eHliMzVnZz09	4513	t	\N	0	0	0.00		2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
324358	\N	Katie	Ramoley	4590	4345	2025-06-24 19:48:53.831168-05	nndz-WkMrNndMN3dnZz09	4513	t	\N	3	9	25.00		2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
324359	\N	Sarah	Rothman	4590	4345	2025-06-24 19:48:53.831168-05	nndz-WkM2eHliMzVqQT09	4513	t	\N	0	5	0.00		2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
324360	\N	Gillian	Climo	4590	4345	2025-06-24 19:48:53.831168-05	nndz-WlNlL3lieitoQT09	4513	t	\N	0	0	0.00		2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
324361	\N	Natalie	Jeannin	4590	4345	2025-06-24 19:48:53.831168-05	nndz-WkM2eHliei9oUT09	4513	t	\N	3	3	50.00		2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
324362	\N	Maggie	Schweitzer	4590	4345	2025-06-24 19:48:53.831168-05	nndz-WlNlL3lieitoUT09	4513	t	\N	12	9	57.10		2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
324363	\N	Katie	Stritch	4590	4345	2025-06-24 19:48:53.831168-05	nndz-WlNlL3hyajhnQT09	4513	t	\N	6	2	75.00		2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
324364	\N	Joann	Williams	4590	4345	2025-06-24 19:48:53.831168-05	nndz-WkM2eHliMzRnUT09	4513	t	\N	2	4	33.30		2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
324365	\N	Marcia	Kenner	4599	4330	2025-06-24 19:48:53.831168-05	nndz-WkNDK3lMYndoZz09	4513	t	\N	5	1	83.30	C	2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
324366	\N	Aubrey	Banks	4599	4330	2025-06-24 19:48:53.831168-05	nndz-WkM2eHhyci9ndz09	4513	t	\N	24	6	80.00		2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
324367	\N	Sean	Barth	4599	4330	2025-06-24 19:48:53.831168-05	nndz-WkNDOHlMdndoQT09	4513	t	\N	7	1	87.50		2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
324368	\N	Sydney	Berens	4599	4330	2025-06-24 19:48:53.831168-05	nndz-WkNDOHlMdnhnZz09	4513	t	\N	17	11	60.70		2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
324369	\N	Kari	Falls	4599	4330	2025-06-24 19:48:53.831168-05	nndz-WkNDOHlMdjloZz09	4513	t	\N	7	1	87.50		2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
324370	\N	Naz	Green	4599	4330	2025-06-24 19:48:53.831168-05	nndz-WkM2eHhMbitnQT09	4513	t	\N	7	1	87.50		2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
324371	\N	Danielle	Malles	4599	4330	2025-06-24 19:48:53.831168-05	nndz-WkNDOHlMbjZqQT09	4513	t	\N	4	4	50.00		2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
324372	\N	Kim	Moore	4599	4330	2025-06-24 19:48:53.831168-05	nndz-WkNDeHdiNzVnZz09	4513	t	\N	0	1	0.00		2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
324373	\N	Angela	Riedel	4599	4330	2025-06-24 19:48:53.831168-05	nndz-WkM2eHhMbitndz09	4513	t	\N	1	1	50.00		2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
324374	\N	Kelly	Schmidgall	4599	4330	2025-06-24 19:48:53.831168-05	nndz-WkM2eHhMZjlnZz09	4513	t	\N	7	1	87.50		2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
324375	\N	Julia	Sierks	4599	4330	2025-06-24 19:48:53.831168-05	nndz-WkNDOHlMdjlodz09	4513	t	\N	2	2	50.00		2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
324376	\N	Erica	Zipp	4599	4330	2025-06-24 19:48:53.831168-05	nndz-WkM2d3dyajlndz09	4513	t	\N	0	2	0.00		2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
324377	\N	Ashley	Podraza	4603	4330	2025-06-24 19:48:53.831168-05	nndz-WkM2eHhMYjhnQT09	4513	t	\N	11	12	47.80	C	2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
324378	\N	Josie	Croll	4603	4330	2025-06-24 19:48:53.831168-05	nndz-WkNDOHlMajhoQT09	4513	t	\N	13	8	61.90	CC	2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
324379	\N	Elissa	Brebach	4603	4330	2025-06-24 19:48:53.831168-05	nndz-WkNDOHlMLytoQT09	4513	t	\N	4	2	66.70		2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
324380	\N	Sunatcha	Breslow	4603	4330	2025-06-24 19:48:53.831168-05	nndz-WlNlN3diZjdnUT09	4513	t	\N	0	1	0.00		2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
324381	\N	Carolyn	Caruso	4603	4330	2025-06-24 19:48:53.831168-05	nndz-WkNHNXhycndnZz09	4513	t	\N	10	8	55.60		2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
324382	\N	Arlene	Frommer	4603	4330	2025-06-24 19:48:53.831168-05	nndz-WkNDOHlMNy9nQT09	4513	t	\N	0	0	0.00		2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
324383	\N	Ania	Kazakevich	4603	4330	2025-06-24 19:48:53.831168-05	nndz-WkNDOHlMbjdoUT09	4513	t	\N	0	1	0.00		2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
324384	\N	Olga	Martinsone	4603	4330	2025-06-24 19:48:53.831168-05	nndz-WkM2eHhidi9qUT09	4513	t	\N	12	11	52.20		2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
324385	\N	Ronnie	Noethlich	4603	4330	2025-06-24 19:48:53.831168-05	nndz-WkNDOHlMdjlqUT09	4513	t	\N	4	5	44.40		2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
324386	\N	Shannon	O'Neil	4603	4330	2025-06-24 19:48:53.831168-05	nndz-WkNDOHlMbndoUT09	4513	t	\N	0	0	0.00		2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
324387	\N	Anne	Ordway	4603	4330	2025-06-24 19:48:53.831168-05	nndz-WkNDOHlMLytoUT09	4513	t	\N	7	10	41.20		2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
324388	\N	Crystal	Pepper	4603	4330	2025-06-24 19:48:53.831168-05	nndz-WkNDOHlMLytnUT09	4513	t	\N	1	3	25.00		2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
324389	\N	Linda	Secord	4603	4330	2025-06-24 19:48:53.831168-05	nndz-WlNlOXhMendoZz09	4513	t	\N	0	0	0.00		2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
324390	\N	Maggie	Tepas	4603	4330	2025-06-24 19:48:53.831168-05	nndz-WkNDOHlML3hodz09	4513	t	\N	10	13	43.50		2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
324391	\N	Susan	Flynn	4608	4330	2025-06-24 19:48:53.831168-05	nndz-WkNDOHlMejVqUT09	4513	t	\N	4	2	66.70	C	2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
324392	\N	Chelsea	Nusslock	4608	4330	2025-06-24 19:48:53.831168-05	nndz-WkNDOHlMdjZqQT09	4513	t	\N	17	6	73.90	CC	2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
324393	\N	Kathy	Dodd	4608	4330	2025-06-24 19:48:53.831168-05	nndz-WkNDOHlMajdqUT09	4513	t	\N	3	2	60.00		2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
324394	\N	Avis	Jason	4608	4330	2025-06-24 19:48:53.831168-05	nndz-WkM2eHliNzdoZz09	4513	t	\N	11	11	50.00		2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
324395	\N	Sheila	Kennedy	4608	4330	2025-06-24 19:48:53.831168-05	nndz-WkNDOHlMejRodz09	4513	t	\N	3	4	42.90		2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
324396	\N	Martha	Leinenweber	4608	4330	2025-06-24 19:48:53.831168-05	nndz-WkNDOHlMbi9qUT09	4513	t	\N	1	6	14.30		2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
324397	\N	Stephanie	Mcguire	4608	4330	2025-06-24 19:48:53.831168-05	nndz-WkNDOHlMejVoQT09	4513	t	\N	1	4	20.00		2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
324398	\N	Laura	Mostofi	4608	4330	2025-06-24 19:48:53.831168-05	nndz-WkNDOHlMNy9odz09	4513	t	\N	1	4	20.00		2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
324399	\N	Laura	Noble	4608	4330	2025-06-24 19:48:53.831168-05	nndz-WkNDOHlMejVqQT09	4513	t	\N	1	8	11.10		2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
324400	\N	Jenny	Sterrett	4608	4330	2025-06-24 19:48:53.831168-05	nndz-WkNDOHlMajdqQT09	4513	t	\N	4	3	57.10		2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
324401	\N	Macaire	Trapp	4608	4330	2025-06-24 19:48:53.831168-05	nndz-WkNDOHlMejVnUT09	4513	t	\N	3	5	37.50		2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
324402	\N	Julie	Adrianopoli	4608	4330	2025-06-24 19:48:53.831168-05	nndz-WkM2eHhMZitqUT09	4513	t	\N	8	4	66.70		2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
324403	\N	Bridget	Kirkendall	4608	4330	2025-06-24 19:48:53.831168-05	nndz-WkNDOHlMejdnUT09	4513	t	\N	4	3	57.10		2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
324404	\N	Kristen	Lipsey	4608	4330	2025-06-24 19:48:53.831168-05	nndz-WkNDOHlMN3dnUT09	4513	t	\N	5	3	62.50		2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
324405	\N	Cathy	McCulloch	4608	4330	2025-06-24 19:48:53.831168-05	nndz-WkNDOHlMejRnZz09	4513	t	\N	2	5	28.60		2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
324406	\N	Chantal	Meier	4608	4330	2025-06-24 19:48:53.831168-05	nndz-WkNDOHlMNy9oZz09	4513	t	\N	6	5	54.50		2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
324407	\N	Catherine	Sullivan - MSC	4608	4330	2025-06-24 19:48:53.831168-05	nndz-WkNDOHlMejRoZz09	4513	t	\N	4	3	57.10		2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
324408	\N	Stacy	Brown	4610	4330	2025-06-24 19:48:53.831168-05	nndz-WkNDOHlMajhqQT09	4513	t	\N	4	8	33.30	C	2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
324409	\N	Sandy	Cvetkovic	4610	4330	2025-06-24 19:48:53.831168-05	nndz-WkNDOHlMMzlnQT09	4513	t	\N	4	8	33.30	CC	2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
324410	\N	Sally	Cottingham	4610	4330	2025-06-24 19:48:53.831168-05	nndz-WkM2eHlMNzZnUT09	4513	t	\N	5	6	45.50		2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
324411	\N	Cynthya	Goulet	4610	4330	2025-06-24 19:48:53.831168-05	nndz-WlNlN3dMaitoZz09	4513	t	\N	0	0	0.00		2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
324412	\N	Jen	Johnson	4610	4330	2025-06-24 19:48:53.831168-05	nndz-WkNDOHlMNytqUT09	4513	t	\N	7	11	38.90		2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
324413	\N	Elizabeth	Kobak	4610	4330	2025-06-24 19:48:53.831168-05	nndz-WlNhNnc3anhndz09	4513	t	\N	0	1	0.00		2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
324414	\N	Kristin	Kranias	4610	4330	2025-06-24 19:48:53.831168-05	nndz-WkNDOHlMdjdnQT09	4513	t	\N	5	7	41.70		2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
324415	\N	Rene	Lederman	4610	4330	2025-06-24 19:48:53.831168-05	nndz-WlNlN3dMYjZnQT09	4513	t	\N	0	0	0.00		2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
324416	\N	Sophia	Naiditch	4610	4330	2025-06-24 19:48:53.831168-05	nndz-WkNDOHlMN3hoZz09	4513	t	\N	1	3	25.00		2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
324417	\N	Elaine	Ni	4610	4330	2025-06-24 19:48:53.831168-05	nndz-WlNlN3g3cjRnUT09	4513	t	\N	7	10	41.20		2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
324418	\N	Nancy	Prosko	4610	4330	2025-06-24 19:48:53.831168-05	nndz-WkNDL3diNy9oZz09	4513	t	\N	2	7	22.20		2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
324419	\N	Alexis	Prousis	4610	4330	2025-06-24 19:48:53.831168-05	nndz-WkNHNXlMMzloQT09	4513	t	\N	0	0	0.00		2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
324420	\N	Janet	Rauschenberger	4610	4330	2025-06-24 19:48:53.831168-05	nndz-WkNDOHlMN3hnZz09	4513	t	\N	1	6	14.30		2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
324421	\N	Gayle	Rudman	4610	4330	2025-06-24 19:48:53.831168-05	nndz-WkM2eHhMYitnQT09	4513	t	\N	3	7	30.00		2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
324422	\N	Stephanie	Frei	4610	4330	2025-06-24 19:48:53.831168-05	nndz-WkMrN3g3endnQT09	4513	t	\N	0	0	0.00		2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
324423	\N	Erin	Alvarez	4610	4330	2025-06-24 19:48:53.831168-05	nndz-WkNHNXdMbitnUT09	4513	t	\N	5	3	62.50		2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
324424	\N	LorRhonda	Miller	4610	4330	2025-06-24 19:48:53.831168-05	nndz-WkNDOHlMMy9nZz09	4513	t	\N	11	2	84.60		2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
324425	\N	Elizabeth	Mihas	4631	4330	2025-06-24 19:48:53.831168-05	nndz-WkNDOHlMdjRoQT09	4513	t	\N	5	15	25.00	C	2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
324426	\N	Clea	Costa	4631	4330	2025-06-24 19:48:53.831168-05	nndz-WkNDOHlMdjVnZz09	4513	t	\N	0	0	0.00		2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
324427	\N	Liz	Cruz	4631	4330	2025-06-24 19:48:53.831168-05	nndz-WkM2eHhidi9nQT09	4513	t	\N	15	7	68.20		2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
324428	\N	Laura	Davis	4631	4330	2025-06-24 19:48:53.831168-05	nndz-WkNDOHlMMzhodz09	4513	t	\N	3	2	60.00		2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
324429	\N	Nicole	Kitsuse	4631	4330	2025-06-24 19:48:53.831168-05	nndz-WlNlNnhyNzRqQT09	4513	t	\N	10	11	47.60		2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
324430	\N	Heather	McWilliams	4631	4330	2025-06-24 19:48:53.831168-05	nndz-WkNDK3hiZi9nUT09	4513	t	\N	10	9	52.60		2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
324431	\N	Alice	Pacaut	4631	4330	2025-06-24 19:48:53.831168-05	nndz-WkNDOHlMLy9qQT09	4513	t	\N	3	6	33.30		2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
324432	\N	Stef	Ross	4631	4330	2025-06-24 19:48:53.831168-05	nndz-WkNDOHlMMzlnUT09	4513	t	\N	4	5	44.40		2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
324433	\N	Jenny	Schuler	4631	4330	2025-06-24 19:48:53.831168-05	nndz-WkNDOHlMdjVndz09	4513	t	\N	0	0	0.00		2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
324434	\N	Margie	Stineman	4631	4330	2025-06-24 19:48:53.831168-05	nndz-WkNDOHlMMzhndz09	4513	t	\N	2	4	33.30		2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
324435	\N	Kaitlin	Ulbert	4631	4330	2025-06-24 19:48:53.831168-05	nndz-WkM2eHlManhnZz09	4513	t	\N	2	10	16.70		2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
324436	\N	Sandy	Wang	4631	4330	2025-06-24 19:48:53.831168-05	nndz-WkNDOHlMejRnUT09	4513	t	\N	12	21	36.40		2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
324437	\N	Laurie	Yorke	4631	4330	2025-06-24 19:48:53.831168-05	nndz-WkNDOHlMdjRoUT09	4513	t	\N	1	5	16.70		2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
324438	\N	Elizabeth	Denison	4631	4330	2025-06-24 19:48:53.831168-05	nndz-WkMreHlicjlqUT09	4513	t	\N	2	6	25.00		2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
324439	\N	Jacqueline	Griesdorn	4631	4330	2025-06-24 19:48:53.831168-05	nndz-WkNDL3diN3dndz09	4513	t	\N	2	3	40.00		2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
324440	\N	Tara	Marsh	4631	4330	2025-06-24 19:48:53.831168-05	nndz-WkNDOHlManhqUT09	4513	t	\N	1	3	25.00		2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
324441	\N	Carla	Sanchez-Palacios	4631	4330	2025-06-24 19:48:53.831168-05	nndz-WkNDL3diN3dnQT09	4513	t	\N	3	7	30.00		2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
324442	\N	Vicki	Lee	4637	4330	2025-06-24 19:48:53.831168-05	nndz-WkNDOHlMcjRnZz09	4513	t	\N	3	3	50.00	C	2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
324443	\N	Irene	Benedict	4637	4330	2025-06-24 19:48:53.831168-05	nndz-WkNDOHlMcjRndz09	4513	t	\N	4	3	57.10		2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
324444	\N	Hallie	Bodman	4637	4330	2025-06-24 19:48:53.831168-05	nndz-WkNDOHlMcjVqQT09	4513	t	\N	1	5	16.70		2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
324445	\N	Christa	Bolt	4637	4330	2025-06-24 19:48:53.831168-05	nndz-WkNDOHlMandqQT09	4513	t	\N	0	1	0.00		2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
324446	\N	Jenny	Damon	4637	4330	2025-06-24 19:48:53.831168-05	nndz-WkNDOHlMdi9odz09	4513	t	\N	9	8	52.90		2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
324447	\N	Susie	Davis	4637	4330	2025-06-24 19:48:53.831168-05	nndz-WkNDOHlMcjVqUT09	4513	t	\N	4	3	57.10		2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
324448	\N	Alison	Donnelly	4637	4330	2025-06-24 19:48:53.831168-05	nndz-WkNDL3diZi9nUT09	4513	t	\N	6	7	46.20		2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
324449	\N	Liz	Hayward	4637	4330	2025-06-24 19:48:53.831168-05	nndz-WkNDOHlMcjRodz09	4513	t	\N	0	4	0.00		2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
324450	\N	Brooke	Timmerman	4637	4330	2025-06-24 19:48:53.831168-05	nndz-WkNDOHlMcjRoZz09	4513	t	\N	5	10	33.30		2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
324451	\N	Mary	Kate Washelesky	4637	4330	2025-06-24 19:48:53.831168-05	nndz-WkM2eHhMbitnZz09	4513	t	\N	6	2	75.00		2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
324452	\N	Shannon	Weasler	4637	4330	2025-06-24 19:48:53.831168-05	nndz-WkNDOHlMcjdoUT09	4513	t	\N	3	2	60.00		2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
324453	\N	Cyndi	Barrett	4637	4330	2025-06-24 19:48:53.831168-05	nndz-WkNDOHlMcjdqQT09	4513	t	\N	0	0	0.00		2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
324454	\N	Andi	Bolan	4637	4330	2025-06-24 19:48:53.831168-05	nndz-WkNDOHlMcjdnQT09	4513	t	\N	0	0	0.00		2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
324455	\N	Lauren	Silverman	4637	4330	2025-06-24 19:48:53.831168-05	nndz-WkM2eHg3bjloQT09	4513	t	\N	4	8	33.30		2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
324456	\N	Molly	Tatham	4637	4330	2025-06-24 19:48:53.831168-05	nndz-WkNDOHlMandnUT09	4513	t	\N	0	0	0.00		2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
324457	\N	Anne	Hendricks	4646	4330	2025-06-24 19:48:53.831168-05	nndz-WkNDOHlMLzdoUT09	4513	t	\N	6	5	54.50	C	2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
324458	\N	Emily	Heinlein	4646	4330	2025-06-24 19:48:53.831168-05	nndz-WkNDOHlMdjVnUT09	4513	t	\N	2	4	33.30	CC	2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
324459	\N	Audra	Billmeyer	4646	4330	2025-06-24 19:48:53.831168-05	nndz-WkNDOHlMbnhoUT09	4513	t	\N	15	7	68.20		2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
324460	\N	Annie	Flanagan	4646	4330	2025-06-24 19:48:53.831168-05	nndz-WkNDOHlMLzVnUT09	4513	t	\N	2	5	28.60		2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
324461	\N	Karen	Fusco	4646	4330	2025-06-24 19:48:53.831168-05	nndz-WkNDOHlMbjZnZz09	4513	t	\N	3	4	42.90		2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
324462	\N	Chris	Maglocci	4646	4330	2025-06-24 19:48:53.831168-05	nndz-WkNDOHlMejVoUT09	4513	t	\N	0	0	0.00		2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
324463	\N	Julie	Reighard	4646	4330	2025-06-24 19:48:53.831168-05	nndz-WkNDOHlMdnhqUT09	4513	t	\N	5	3	62.50		2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
324464	\N	Cassie	Rose	4646	4330	2025-06-24 19:48:53.831168-05	nndz-WkNDOHlMdndndz09	4513	t	\N	14	6	70.00		2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
324465	\N	Shannon	Weber	4646	4330	2025-06-24 19:48:53.831168-05	nndz-WkNDOHlMai9odz09	4513	t	\N	8	5	61.50		2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
324466	\N	Marianne	Zidar	4646	4330	2025-06-24 19:48:53.831168-05	nndz-WkNDOHlMdnhqQT09	4513	t	\N	5	4	55.60		2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
324467	\N	Gabby	Blinn	4646	4330	2025-06-24 19:48:53.831168-05	nndz-WkNDOHlMMzVodz09	4513	t	\N	10	6	62.50		2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
324468	\N	Julie	Fish	4646	4330	2025-06-24 19:48:53.831168-05	nndz-WkM2eHhMYjVoQT09	4513	t	\N	4	4	50.00		2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
324469	\N	January	Stramaglia	4646	4330	2025-06-24 19:48:53.831168-05	nndz-WkM2eHliLytoUT09	4513	t	\N	10	9	52.60		2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
324470	\N	Stefanie	Bell	4571	4346	2025-06-24 19:48:53.831168-05	nndz-WkNDOHlMbnhnUT09	4513	t	\N	6	11	35.30	C	2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
324471	\N	Debbie	Shiner	4571	4346	2025-06-24 19:48:53.831168-05	nndz-WkNDOHlMbjlnZz09	4513	t	\N	0	6	0.00	CC	2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
324472	\N	Lindsay	Cohen	4571	4346	2025-06-24 19:48:53.831168-05	nndz-WkNHNXdyejRodz09	4513	t	\N	10	5	66.70		2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
324473	\N	Tracy	Freed	4571	4346	2025-06-24 19:48:53.831168-05	nndz-WkNDOHlMMytqQT09	4513	t	\N	2	6	25.00		2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
324474	\N	Lizzie	Gottlieb	4571	4346	2025-06-24 19:48:53.831168-05	nndz-WkNDOHlMM3hodz09	4513	t	\N	2	10	16.70		2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
324475	\N	Laura	Isaacson	4571	4346	2025-06-24 19:48:53.831168-05	nndz-WkNDOHlMMytqUT09	4513	t	\N	3	6	33.30		2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
324476	\N	Julie	Jacobs	4571	4346	2025-06-24 19:48:53.831168-05	nndz-WkNDOHlMYjRnZz09	4513	t	\N	2	9	18.20		2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
324477	\N	Jill	Schlossberg	4571	4346	2025-06-24 19:48:53.831168-05	nndz-WkNDOHlMN3hnQT09	4513	t	\N	0	1	0.00		2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
324478	\N	Rachel	Wanroy	4571	4346	2025-06-24 19:48:53.831168-05	nndz-WkM2eHlML3dnQT09	4513	t	\N	2	10	16.70		2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
324479	\N	Stacy	Weiss	4571	4346	2025-06-24 19:48:53.831168-05	nndz-WkNDOHlMbjVoQT09	4513	t	\N	2	6	25.00		2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
324480	\N	Cheryl	Imo	4579	4346	2025-06-24 19:48:53.831168-05	nndz-WkNDOHlMNytnUT09	4513	t	\N	9	10	47.40	C	2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
324481	\N	Nicole	Petsos	4579	4346	2025-06-24 19:48:53.831168-05	nndz-WkM2eHhMYjRndz09	4513	t	\N	8	7	53.30	CC	2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
324482	\N	Michelle	Abrahamson	4579	4346	2025-06-24 19:48:53.831168-05	nndz-WkNDOHlMN3hqUT09	4513	t	\N	0	0	0.00		2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
324483	\N	Darragh	Blachno	4579	4346	2025-06-24 19:48:53.831168-05	nndz-WkNDL3dienhoZz09	4513	t	\N	2	6	25.00		2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
324484	\N	Rebecca	Guryan	4579	4346	2025-06-24 19:48:53.831168-05	nndz-WkNDOHlMN3dndz09	4513	t	\N	2	6	25.00		2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
324485	\N	Julie	Gustafson	4579	4346	2025-06-24 19:48:53.831168-05	nndz-WkNDOHlMLzhnUT09	4513	t	\N	2	8	20.00		2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
324486	\N	Karen	Hutchinson	4579	4346	2025-06-24 19:48:53.831168-05	nndz-WkNDOHlMandnQT09	4513	t	\N	2	4	33.30		2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
324487	\N	Becky	Kremin	4579	4346	2025-06-24 19:48:53.831168-05	nndz-WkNDOHlMN3hqQT09	4513	t	\N	1	6	14.30		2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
324488	\N	Stephanie	Layden	4579	4346	2025-06-24 19:48:53.831168-05	nndz-WkNDOHlMN3dodz09	4513	t	\N	1	5	16.70		2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
324489	\N	Denise	Mulica	4579	4346	2025-06-24 19:48:53.831168-05	nndz-WkNDOHlMN3doZz09	4513	t	\N	2	4	33.30		2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
324490	\N	Laura-Min	Proctor	4579	4346	2025-06-24 19:48:53.831168-05	nndz-WkM2eHg3LzRndz09	4513	t	\N	2	5	28.60		2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
324491	\N	Keri	Roth	4579	4346	2025-06-24 19:48:53.831168-05	nndz-WkM2eHliei9nQT09	4513	t	\N	0	0	0.00		2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
324492	\N	Stacy	Salgado	4579	4346	2025-06-24 19:48:53.831168-05	nndz-WkMrK3c3LzRoZz09	4513	t	\N	3	6	33.30		2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
324493	\N	Sandy	Sherwood	4579	4346	2025-06-24 19:48:53.831168-05	nndz-WkNHNXc3ajVoUT09	4513	t	\N	0	1	0.00		2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
324494	\N	Mary	Tritley	4593	4346	2025-06-24 19:48:53.831168-05	nndz-WkNDOHlMLzZnZz09	4513	t	\N	2	4	33.30	C	2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
324495	\N	Paget	Bahr	4593	4346	2025-06-24 19:48:53.831168-05	nndz-WkNDOHlMLzloUT09	4513	t	\N	2	4	33.30	CC	2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
324496	\N	Julie	Backer	4593	4346	2025-06-24 19:48:53.831168-05	nndz-WkNDOHlMLzZndz09	4513	t	\N	1	3	25.00		2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
324497	\N	Kim	Chatain	4593	4346	2025-06-24 19:48:53.831168-05	nndz-WkNDOHlMbndoZz09	4513	t	\N	0	4	0.00		2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
324498	\N	Mirian	Cruz	4593	4346	2025-06-24 19:48:53.831168-05	nndz-WkNDeHdiLytnQT09	4513	t	\N	6	0	100.00		2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
324499	\N	Anne	Faurot	4593	4346	2025-06-24 19:48:53.831168-05	nndz-WkNDOHlMLzdoQT09	4513	t	\N	1	3	25.00		2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
324500	\N	Louise	Flickinger	4593	4346	2025-06-24 19:48:53.831168-05	nndz-WkNDOHlMLzlqQT09	4513	t	\N	6	3	66.70		2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
324501	\N	Mary	Griffin	4593	4346	2025-06-24 19:48:53.831168-05	nndz-WkNDOHlMLzRnUT09	4513	t	\N	3	5	37.50		2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
324502	\N	Sally	Jones	4593	4346	2025-06-24 19:48:53.831168-05	nndz-WkNDOHlMajdndz09	4513	t	\N	10	0	100.00		2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
324503	\N	Sarah	Magner	4593	4346	2025-06-24 19:48:53.831168-05	nndz-WkNDOHlMLzloQT09	4513	t	\N	0	4	0.00		2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
324504	\N	Kathryn	Mangel	4593	4346	2025-06-24 19:48:53.831168-05	nndz-WkNDOHlMLzlnUT09	4513	t	\N	1	6	14.30		2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
324505	\N	Karie	Smith	4593	4346	2025-06-24 19:48:53.831168-05	nndz-WkM2eHg3NytqQT09	4513	t	\N	6	6	50.00		2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
324506	\N	Kathryn	Talty	4593	4346	2025-06-24 19:48:53.831168-05	nndz-WkNDOHlMLzZodz09	4513	t	\N	0	3	0.00		2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
324507	\N	Kristen	Klauke	4593	4346	2025-06-24 19:48:53.831168-05	nndz-WkNDOHlMLzVndz09	4513	t	\N	0	0	0.00		2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
324508	\N	Jane	McNitt	4593	4346	2025-06-24 19:48:53.831168-05	nndz-WkNDK3lMZi9oQT09	4513	t	\N	0	0	0.00		2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
324509	\N	Susan	Patterson	4593	4346	2025-06-24 19:48:53.831168-05	nndz-WkNDOHlMLzRqUT09	4513	t	\N	0	0	0.00		2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
324510	\N	Susan	Quigley	4593	4346	2025-06-24 19:48:53.831168-05	nndz-WkNDOHlMLzVnZz09	4513	t	\N	0	0	0.00		2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
324511	\N	Wendy	Yamada	4593	4346	2025-06-24 19:48:53.831168-05	nndz-WkNDOHlMbjhnQT09	4513	t	\N	0	0	0.00		2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
324512	\N	Julie	Hockenberg	4601	4346	2025-06-24 19:48:53.831168-05	nndz-WkNDOHlMenhndz09	4513	t	\N	13	5	72.20	C	2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
324513	\N	Nicky	Bliwas	4601	4346	2025-06-24 19:48:53.831168-05	nndz-WkNDOHlMZjhndz09	4513	t	\N	3	3	50.00		2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
324514	\N	Buddy	Erwin	4601	4346	2025-06-24 19:48:53.831168-05	nndz-WkM2eHhyM3hodz09	4513	t	\N	6	8	42.90		2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
324515	\N	Deb	Hirschfield	4601	4346	2025-06-24 19:48:53.831168-05	nndz-WkNDOHlMenhodz09	4513	t	\N	0	0	0.00		2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
324516	\N	Elizabeth	Hutchins	4601	4346	2025-06-24 19:48:53.831168-05	nndz-WkM2eHhMajlndz09	4513	t	\N	8	7	53.30		2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
324517	\N	Lizzie	Kaplan Ginsberg	4601	4346	2025-06-24 19:48:53.831168-05	nndz-WkM2eHhMYnhoQT09	4513	t	\N	5	2	71.40		2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
324518	\N	Julie	Klaff	4601	4346	2025-06-24 19:48:53.831168-05	nndz-WkM2eHhMYnhnQT09	4513	t	\N	12	5	70.60		2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
324519	\N	Liz	Kulakofsky	4601	4346	2025-06-24 19:48:53.831168-05	nndz-WkNHNHhMYnhnUT09	4513	t	\N	2	4	33.30		2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
324520	\N	Ashley	Lebovic	4601	4346	2025-06-24 19:48:53.831168-05	nndz-WkNDOHlMenhnZz09	4513	t	\N	13	5	72.20		2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
324521	\N	Brooke	Levine	4601	4346	2025-06-24 19:48:53.831168-05	nndz-WkNDOHlMajlnQT09	4513	t	\N	0	0	0.00		2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
324522	\N	Jen	Meyers	4601	4346	2025-06-24 19:48:53.831168-05	nndz-WkNDOHlMditndz09	4513	t	\N	2	5	28.60		2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
324523	\N	Cathy	Ross	4601	4346	2025-06-24 19:48:53.831168-05	nndz-WkNDOHlMbi9ndz09	4513	t	\N	0	0	0.00		2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
324524	\N	Lindsey	Ross	4601	4346	2025-06-24 19:48:53.831168-05	nndz-WkM2eHhMYnhnZz09	4513	t	\N	3	0	100.00		2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
324525	\N	marla	stone	4601	4346	2025-06-24 19:48:53.831168-05	nndz-WkNDOHlMdi9qQT09	4513	t	\N	0	3	0.00		2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
324526	\N	Stacey	Cavanagh	4611	4346	2025-06-24 19:48:53.831168-05	nndz-WkNDOHlMejlnZz09	4513	t	\N	6	2	75.00	C	2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
324527	\N	Kelly	Kenny	4611	4346	2025-06-24 19:48:53.831168-05	nndz-WkNDOHlMejloZz09	4513	t	\N	1	1	50.00	CC	2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
324528	\N	Sandy	Fencik	4611	4346	2025-06-24 19:48:53.831168-05	nndz-WkNDOHlMMzlqUT09	4513	t	\N	5	2	71.40		2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
324529	\N	Yvette	Finegan	4611	4346	2025-06-24 19:48:53.831168-05	nndz-WkNDOHlMejZnQT09	4513	t	\N	5	2	71.40		2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
324530	\N	Spencer	Granger	4611	4346	2025-06-24 19:48:53.831168-05	nndz-WkNDOHlMMzlndz09	4513	t	\N	7	0	100.00		2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
324531	\N	Lindsay	Grieco	4611	4346	2025-06-24 19:48:53.831168-05	nndz-WkM2eHhMYjdodz09	4513	t	\N	6	0	100.00		2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
324532	\N	Audrey	Koopsen Boucquemont	4611	4346	2025-06-24 19:48:53.831168-05	nndz-WkNDOHlMdjlnZz09	4513	t	\N	12	5	70.60		2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
324533	\N	Katie	Mangan	4611	4346	2025-06-24 19:48:53.831168-05	nndz-WkNDOHlMejZnUT09	4513	t	\N	4	0	100.00		2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
324534	\N	Elizabeth	Pontarelli	4611	4346	2025-06-24 19:48:53.831168-05	nndz-WkNDOHlMaitoZz09	4513	t	\N	7	2	77.80		2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
324535	\N	Maggie	Reynolds	4611	4346	2025-06-24 19:48:53.831168-05	nndz-WkNDOHlMejZqUT09	4513	t	\N	5	3	62.50		2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
324536	\N	Julie	Schirmang	4611	4346	2025-06-24 19:48:53.831168-05	nndz-WkNDOHlMaitnZz09	4513	t	\N	6	1	85.70		2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
324537	\N	Carey	Gifford	4611	4346	2025-06-24 19:48:53.831168-05	nndz-WkNDOHlMejZqQT09	4513	t	\N	0	1	0.00		2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
324538	\N	Colleen	Levitz	4611	4346	2025-06-24 19:48:53.831168-05	nndz-WkNDOHlMejZoZz09	4513	t	\N	1	7	12.50		2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
324539	\N	MJ	Murnane	4611	4346	2025-06-24 19:48:53.831168-05	nndz-WkNDOHlMejZodz09	4513	t	\N	3	2	60.00		2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
324540	\N	Stephanie	Selby	4611	4346	2025-06-24 19:48:53.831168-05	nndz-WkM2eHhycnhoZz09	4513	t	\N	10	5	66.70		2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
324541	\N	Andi	Daube	4612	4346	2025-06-24 19:48:53.831168-05	nndz-WkNDOHlMLzlndz09	4513	t	\N	4	3	57.10	C	2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
324542	\N	Dani	Zepeda	4612	4346	2025-06-24 19:48:53.831168-05	nndz-WkM2d3dybjVnQT09	4513	t	\N	1	10	9.10	CC	2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
324543	\N	Susan	Becker	4612	4346	2025-06-24 19:48:53.831168-05	nndz-WkNDOHlMajhndz09	4513	t	\N	2	5	28.60		2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
324544	\N	Terri	Gordon	4612	4346	2025-06-24 19:48:53.831168-05	nndz-WkNDOHlMLzlodz09	4513	t	\N	1	5	16.70		2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
324545	\N	Liane	Joseph	4612	4346	2025-06-24 19:48:53.831168-05	nndz-WkNDOHlMLzhoQT09	4513	t	\N	0	0	0.00		2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
324546	\N	Debi	Learner	4612	4346	2025-06-24 19:48:53.831168-05	nndz-WkMrN3hyenhqQT09	4513	t	\N	0	0	0.00		2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
324547	\N	Liz	Lund	4612	4346	2025-06-24 19:48:53.831168-05	nndz-WkNDOHlMLzloZz09	4513	t	\N	3	5	37.50		2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
324548	\N	Julie	Miller	4612	4346	2025-06-24 19:48:53.831168-05	nndz-WkNDOHlMLzhoUT09	4513	t	\N	2	4	33.30		2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
324549	\N	Emily	Tresley	4612	4346	2025-06-24 19:48:53.831168-05	nndz-WkMrN3hMLytndz09	4513	t	\N	3	5	37.50		2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
324550	\N	Laura	Ulrich	4612	4346	2025-06-24 19:48:53.831168-05	nndz-WkNDOHlMLzZqQT09	4513	t	\N	3	2	60.00		2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
324551	\N	Rachael	White	4612	4346	2025-06-24 19:48:53.831168-05	nndz-WlNlL3c3YjRnZz09	4513	t	\N	6	1	85.70		2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
324552	\N	Nadine	Woldenberg	4612	4346	2025-06-24 19:48:53.831168-05	nndz-WkNDOHlMLzZqUT09	4513	t	\N	4	5	44.40		2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
324553	\N	Liz	Agins	4612	4346	2025-06-24 19:48:53.831168-05	nndz-WkMrNnc3ajRnZz09	4513	t	\N	0	0	0.00		2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
324554	\N	Stacy	Auslander	4612	4346	2025-06-24 19:48:53.831168-05	nndz-WkM2eHg3YjVndz09	4513	t	\N	7	3	70.00		2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
324555	\N	Susie	Glikin	4612	4346	2025-06-24 19:48:53.831168-05	nndz-WkNDOHlMLzlnZz09	4513	t	\N	0	0	0.00		2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
324556	\N	Christine	Harris	4620	4347	2025-06-24 19:48:53.831168-05	nndz-WkNDOHlMMzRnQT09	4513	t	\N	11	11	50.00	C	2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
324557	\N	Anne	Walker	4620	4347	2025-06-24 19:48:53.831168-05	nndz-WkNDOHlMaitndz09	4513	t	\N	5	6	45.50	CC	2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
324558	\N	Kitty	Bingham	4620	4347	2025-06-24 19:48:53.831168-05	nndz-WkNDOHlMaitqUT09	4513	t	\N	5	2	71.40		2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
324559	\N	Sally	Ann Boyle	4620	4347	2025-06-24 19:48:53.831168-05	nndz-WkNDOHlMdjhoUT09	4513	t	\N	3	8	27.30		2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
324560	\N	Becky	Bucolo	4620	4347	2025-06-24 19:48:53.831168-05	nndz-WkM2eHlManhndz09	4513	t	\N	5	2	71.40		2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
324561	\N	Lisa	Goldberg	4620	4347	2025-06-24 19:48:53.831168-05	nndz-WkNDOHlMbjhqQT09	4513	t	\N	5	11	31.20		2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
324562	\N	Camille	Hoover	4620	4347	2025-06-24 19:48:53.831168-05	nndz-WkM2eHhMYitoQT09	4513	t	\N	6	1	85.70		2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
324563	\N	Ellen	Magrini	4620	4347	2025-06-24 19:48:53.831168-05	nndz-WkNDOHlMYjVnQT09	4513	t	\N	0	0	0.00		2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
324564	\N	Elizabeth	Nassar	4620	4347	2025-06-24 19:48:53.831168-05	nndz-WkNDOHlMdjZnZz09	4513	t	\N	3	3	50.00		2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
324565	\N	Jennifer	Perry	4620	4347	2025-06-24 19:48:53.831168-05	nndz-WkNDOHlML3doUT09	4513	t	\N	14	10	58.30		2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
324566	\N	Meg	Revord	4620	4347	2025-06-24 19:48:53.831168-05	nndz-WkNDOHlMLzRoUT09	4513	t	\N	0	0	0.00		2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
324567	\N	Patti	Wenzel	4620	4347	2025-06-24 19:48:53.831168-05	nndz-WkNDOHlMcitodz09	4513	t	\N	1	3	25.00		2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
324568	\N	Ami	Bilimoria	4620	4347	2025-06-24 19:48:53.831168-05	nndz-WkM2eHhMYjhqQT09	4513	t	\N	0	0	0.00		2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
324569	\N	Suzanne	Finkel	4620	4347	2025-06-24 19:48:53.831168-05	nndz-WkNDOHlMMzRqUT09	4513	t	\N	0	4	0.00		2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
324570	\N	Eileen	Grant	4620	4347	2025-06-24 19:48:53.831168-05	nndz-WkNDOHlMMzdodz09	4513	t	\N	2	2	50.00		2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
324571	\N	Molly	Schmidt	4620	4347	2025-06-24 19:48:53.831168-05	nndz-WkNDOHlMdnhnQT09	4513	t	\N	0	1	0.00		2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
324572	\N	Katy	Reardon	4620	4348	2025-06-24 19:48:53.831168-05	nndz-WkNDOHlMMzRqQT09	4513	t	\N	3	4	42.90	C	2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
324573	\N	Kati	Sciortino	4620	4348	2025-06-24 19:48:53.831168-05	nndz-WkNDOHlMMzRnUT09	4513	t	\N	15	12	55.60	CC	2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
324574	\N	Emily	Buerger	4620	4348	2025-06-24 19:48:53.831168-05	nndz-WkM2eHliNzdoUT09	4513	t	\N	7	6	53.80		2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
324575	\N	Megan	Gemp	4620	4348	2025-06-24 19:48:53.831168-05	nndz-WkNDOHlMYjloQT09	4513	t	\N	3	6	33.30		2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
324576	\N	Megan	Gieselman	4620	4348	2025-06-24 19:48:53.831168-05	nndz-WkNDOHlMdndnZz09	4513	t	\N	3	7	30.00		2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
324577	\N	Katie	Hunt	4620	4348	2025-06-24 19:48:53.831168-05	nndz-WkNHNHhycnhoUT09	4513	t	\N	3	1	75.00		2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
324578	\N	Beth	Kurtzweil	4620	4348	2025-06-24 19:48:53.831168-05	nndz-WkNDOHlMMzZodz09	4513	t	\N	0	6	0.00		2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
324579	\N	Mira	Schwab	4620	4348	2025-06-24 19:48:53.831168-05	nndz-WkNDOHlMYjloUT09	4513	t	\N	4	4	50.00		2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
324580	\N	Amy	Zahorik	4620	4348	2025-06-24 19:48:53.831168-05	nndz-WkNDOHlMbitnZz09	4513	t	\N	2	5	28.60		2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
324581	\N	Suzanne	Finkel	4620	4348	2025-06-24 19:48:53.831168-05	nndz-WkNDOHlMMzRqUT09	4513	t	\N	0	4	0.00		2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
324582	\N	Eileen	Grant	4620	4348	2025-06-24 19:48:53.831168-05	nndz-WkNDOHlMMzdodz09	4513	t	\N	2	2	50.00		2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
324583	\N	Sarah	Leverenz	4620	4348	2025-06-24 19:48:53.831168-05	nndz-WkNDOHlMMzdqUT09	4513	t	\N	0	0	0.00		2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
324584	\N	Diana	Peterson	4620	4348	2025-06-24 19:48:53.831168-05	nndz-WkNDOHlMMzdndz09	4513	t	\N	0	1	0.00		2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
324585	\N	Patti	Wenzel	4620	4348	2025-06-24 19:48:53.831168-05	nndz-WkNDOHlMcitodz09	4513	t	\N	1	3	25.00		2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
324586	\N	Colleen	Wilkins	4620	4348	2025-06-24 19:48:53.831168-05	nndz-WkMrK3dMYjdoUT09	4513	t	\N	5	8	38.50		2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
324587	\N	Brooke	Cornell	4620	4348	2025-06-24 19:48:53.831168-05	nndz-WkM2eHhyditoUT09	4513	t	\N	6	3	66.70		2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
324588	\N	Sarah	Padgitt	4635	4346	2025-06-24 19:48:53.831168-05	nndz-WkNDOHlMandoQT09	4513	t	\N	13	4	76.50	C	2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
324589	\N	Nancy	Poggioli	4635	4346	2025-06-24 19:48:53.831168-05	nndz-WkNDOHlMMzhoQT09	4513	t	\N	5	2	71.40	CC	2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
324590	\N	Sophie	Daavettila	4635	4346	2025-06-24 19:48:53.831168-05	nndz-WlNlN3dyLzlqQT09	4513	t	\N	21	6	77.80		2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
324591	\N	Kim	Fiedler	4635	4346	2025-06-24 19:48:53.831168-05	nndz-WkNDOHlMMzhoUT09	4513	t	\N	6	2	75.00		2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
324592	\N	Grace	Frank	4635	4346	2025-06-24 19:48:53.831168-05	nndz-WkM2eHg3ejhoZz09	4513	t	\N	0	0	0.00		2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
324593	\N	Virginia	Gluckman	4635	4346	2025-06-24 19:48:53.831168-05	nndz-WkNDOHlMdjhoZz09	4513	t	\N	0	0	0.00		2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
324594	\N	Nichole	Humphrey	4635	4346	2025-06-24 19:48:53.831168-05	nndz-WkNDOHlMMzhqQT09	4513	t	\N	9	6	60.00		2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
324595	\N	Beth	Miller	4635	4346	2025-06-24 19:48:53.831168-05	nndz-WkNDOHlMMzlnZz09	4513	t	\N	4	1	80.00		2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
324596	\N	Sally	Tomlinson	4635	4346	2025-06-24 19:48:53.831168-05	nndz-WkNDOHlMbjdodz09	4513	t	\N	7	2	77.80		2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
324597	\N	Sarah	Troglia	4635	4346	2025-06-24 19:48:53.831168-05	nndz-WkNDOHlMMytnZz09	4513	t	\N	8	7	53.30		2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
324598	\N	Beth	Boehrer	4635	4346	2025-06-24 19:48:53.831168-05	nndz-WkNDOHlMMzhnQT09	4513	t	\N	3	1	75.00		2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
324599	\N	Suzy	Cirulis	4635	4346	2025-06-24 19:48:53.831168-05	nndz-WkNHNHlMdjdqUT09	4513	t	\N	8	2	80.00		2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
324600	\N	Susan	Fraser	4635	4346	2025-06-24 19:48:53.831168-05	nndz-WkNDOHlMMzhnUT09	4513	t	\N	0	2	0.00		2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
324601	\N	Tracy	Hedstrom	4635	4346	2025-06-24 19:48:53.831168-05	nndz-WkNDOHlMMzhqUT09	4513	t	\N	0	2	0.00		2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
324602	\N	Katie	Krebs	4635	4346	2025-06-24 19:48:53.831168-05	nndz-WkM2eHhyai9oZz09	4513	t	\N	5	1	83.30		2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
324603	\N	Molly	Osborne	4635	4346	2025-06-24 19:48:53.831168-05	nndz-WkM2eHhyai9nZz09	4513	t	\N	7	1	87.50		2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
324604	\N	Marena	Rudy	4635	4346	2025-06-24 19:48:53.831168-05	nndz-WkM2eHhyajZodz09	4513	t	\N	4	0	100.00		2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
324605	\N	Liz	Smylie	4635	4346	2025-06-24 19:48:53.831168-05	nndz-WkNDL3dicjdoZz09	4513	t	\N	11	9	55.00		2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
324606	\N	Ryan	Statza	4635	4346	2025-06-24 19:48:53.831168-05	nndz-WkM2eHliLytqUT09	4513	t	\N	13	3	81.20		2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
324607	\N	Debbie	Yapp	4635	4346	2025-06-24 19:48:53.831168-05	nndz-WkNDOHlMMytndz09	4513	t	\N	6	2	75.00		2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
324608	\N	Michelle	Petersen	4639	4346	2025-06-24 19:48:53.831168-05	nndz-WkM2d3diL3hoUT09	4513	t	\N	6	1	85.70	C	2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
324609	\N	Julie	B. Miller	4639	4346	2025-06-24 19:48:53.831168-05	nndz-WkNDOHlMbjVnQT09	4513	t	\N	5	6	45.50	CC	2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
324610	\N	Morgan	Azim	4639	4346	2025-06-24 19:48:53.831168-05	nndz-WkM2eHhyYjlodz09	4513	t	\N	7	3	70.00		2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
324611	\N	Katie	Bauer	4639	4346	2025-06-24 19:48:53.831168-05	nndz-WkNDOHlMci9odz09	4513	t	\N	4	3	57.10		2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
324612	\N	Stephanie	Kozak	4639	4346	2025-06-24 19:48:53.831168-05	nndz-WkNDOHlMcjhqUT09	4513	t	\N	3	5	37.50		2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
324613	\N	Maureen	Loftus	4639	4346	2025-06-24 19:48:53.831168-05	nndz-WkNDOHlMcitoQT09	4513	t	\N	4	3	57.10		2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
324614	\N	Katie	Mitchell	4639	4346	2025-06-24 19:48:53.831168-05	nndz-WkNDOHlMci9ndz09	4513	t	\N	3	4	42.90		2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
324615	\N	Michelle	Rupprecht	4639	4346	2025-06-24 19:48:53.831168-05	nndz-WkMrNnc3ditqUT09	4513	t	\N	2	5	28.60		2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
324616	\N	Jen	Unis	4639	4346	2025-06-24 19:48:53.831168-05	nndz-WkNHNHhycitqQT09	4513	t	\N	7	11	38.90		2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
324617	\N	Sara	Veit	4639	4346	2025-06-24 19:48:53.831168-05	nndz-WkM2eHhydjhqQT09	4513	t	\N	9	1	90.00		2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
324618	\N	Shay	Cwick	4639	4346	2025-06-24 19:48:53.831168-05	nndz-WkM2eHhyYnhnZz09	4513	t	\N	8	4	66.70		2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
324619	\N	Nahrin	Marino	4639	4346	2025-06-24 19:48:53.831168-05	nndz-WkM2eHhyYjZnZz09	4513	t	\N	3	2	60.00		2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
324620	\N	Carrie	Early	4575	4349	2025-06-24 19:48:53.831168-05	nndz-WkM2eHlieitoZz09	4513	t	\N	4	5	44.40	C	2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
324621	\N	Kathleen	Passananti	4575	4349	2025-06-24 19:48:53.831168-05	nndz-WkM2eHlieitqQT09	4513	t	\N	7	6	53.80	CC	2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
324622	\N	Helen	Boduch	4575	4349	2025-06-24 19:48:53.831168-05	nndz-WkM2eHliei9nZz09	4513	t	\N	7	5	58.30		2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
324623	\N	Donna	Coffey	4575	4349	2025-06-24 19:48:53.831168-05	nndz-WkM2eHlieitoUT09	4513	t	\N	3	2	60.00		2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
324624	\N	Susan	Draddy	4575	4349	2025-06-24 19:48:53.831168-05	nndz-WkM2eHlieitoQT09	4513	t	\N	2	6	25.00		2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
324625	\N	Gena	Fite	4575	4349	2025-06-24 19:48:53.831168-05	nndz-WlNlNnhiZjdndz09	4513	t	\N	4	2	66.70		2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
324626	\N	Kate	Hickey	4575	4349	2025-06-24 19:48:53.831168-05	nndz-WkM2d3hMM3dndz09	4513	t	\N	5	6	45.50		2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
324627	\N	Donna	Mittelstadt	4575	4349	2025-06-24 19:48:53.831168-05	nndz-WkM2eHlieitqUT09	4513	t	\N	7	4	63.60		2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
324628	\N	Avis	Sparacino	4575	4349	2025-06-24 19:48:53.831168-05	nndz-WkM2eHlienhodz09	4513	t	\N	3	4	42.90		2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
324629	\N	Sharon	Theoharous	4575	4349	2025-06-24 19:48:53.831168-05	nndz-WkM2eHhidi9ndz09	4513	t	\N	0	1	0.00		2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
324630	\N	Trisha	Wilson	4575	4349	2025-06-24 19:48:53.831168-05	nndz-WkMrNnc3ajRoUT09	4513	t	\N	2	7	22.20		2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
324631	\N	Dorothy	Foster	4575	4349	2025-06-24 19:48:53.831168-05	nndz-WkM2eHlieitnUT09	4513	t	\N	3	4	42.90		2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
324632	\N	Lara	Matricaria	4575	4349	2025-06-24 19:48:53.831168-05	nndz-WkM2eHlieitnZz09	4513	t	\N	0	0	0.00		2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
324633	\N	Catherine	Williams	4585	4349	2025-06-24 19:48:53.831168-05	nndz-WkM2eHhyL3hoQT09	4513	t	\N	9	0	100.00	C	2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
324634	\N	Jane	Head	4585	4349	2025-06-24 19:48:53.831168-05	nndz-WkNDOHlMMzVndz09	4513	t	\N	2	2	50.00	CC	2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
324635	\N	Liz	Hayes	4585	4349	2025-06-24 19:48:53.831168-05	nndz-WkNDOHlMbndodz09	4513	t	\N	4	3	57.10		2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
324636	\N	Kelly	Kenney	4585	4349	2025-06-24 19:48:53.831168-05	nndz-WkNDOHlMbjhnUT09	4513	t	\N	7	0	100.00		2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
324637	\N	Rita	Lashmet	4585	4349	2025-06-24 19:48:53.831168-05	nndz-WkNDOHlMejdqUT09	4513	t	\N	0	4	0.00		2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
324638	\N	Adriane	McKnight	4585	4349	2025-06-24 19:48:53.831168-05	nndz-WkNDOHlMMzVoZz09	4513	t	\N	3	5	37.50		2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
324639	\N	Bridget	Schroeder	4585	4349	2025-06-24 19:48:53.831168-05	nndz-WkNDOHlMendqUT09	4513	t	\N	2	4	33.30		2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
324640	\N	Amy	Seaman	4585	4349	2025-06-24 19:48:53.831168-05	nndz-WkNDOHlMMzRoUT09	4513	t	\N	0	6	0.00		2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
324641	\N	Catherine	Sullivan	4585	4349	2025-06-24 19:48:53.831168-05	nndz-WkM2eHlMbjZqQT09	4513	t	\N	2	4	33.30		2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
324642	\N	Sarah	Williams	4585	4349	2025-06-24 19:48:53.831168-05	nndz-WkNDOHlMdnhnUT09	4513	t	\N	4	0	100.00		2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
324643	\N	Mary	Womsley	4585	4349	2025-06-24 19:48:53.831168-05	nndz-WkNDeHdiNzZoUT09	4513	t	\N	3	4	42.90		2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
324644	\N	Peggy	Hopkins	4585	4349	2025-06-24 19:48:53.831168-05	nndz-WkNDOHlMajdoZz09	4513	t	\N	0	0	0.00		2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
324645	\N	Jackie	Thompson	4585	4349	2025-06-24 19:48:53.831168-05	nndz-WkNDOHlMendqQT09	4513	t	\N	1	0	100.00		2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
324646	\N	Mo	Lawler	4585	4349	2025-06-24 19:48:53.831168-05	nndz-WkMrK3lMejdqQT09	4513	t	\N	5	3	62.50		2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
324647	\N	Hillary	Sutton	4585	4349	2025-06-24 19:48:53.831168-05	nndz-WlNlN3hyYjRoUT09	4513	t	\N	6	2	75.00		2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
324648	\N	Katie	London	4590	4349	2025-06-24 19:48:53.831168-05	nndz-WkMrK3g3YjRoUT09	4513	t	\N	8	11	42.10	C	2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
324649	\N	Amy	Agema	4590	4349	2025-06-24 19:48:53.831168-05	nndz-WkMrL3lMejdoZz09	4513	t	\N	9	6	60.00	CC	2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
324650	\N	Heidi	Brock	4590	4349	2025-06-24 19:48:53.831168-05	nndz-WkMrL3lMci9oQT09	4513	t	\N	4	7	36.40		2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
324651	\N	Janelle	Bunn	4590	4349	2025-06-24 19:48:53.831168-05	nndz-WkMreHhibjRqUT09	4513	t	\N	0	0	0.00		2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
324652	\N	Helen	Fang	4590	4349	2025-06-24 19:48:53.831168-05	nndz-WlNhK3dMejlnQT09	4513	t	\N	10	3	76.90		2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
324653	\N	Beth	Jensen	4590	4349	2025-06-24 19:48:53.831168-05	nndz-WkMrNndMN3dndz09	4513	t	\N	7	8	46.70		2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
324654	\N	Christine	Nicholson	4590	4349	2025-06-24 19:48:53.831168-05	nndz-WkMrK3hMdi9ndz09	4513	t	\N	4	3	57.10		2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
324655	\N	Megan	Noell	4590	4349	2025-06-24 19:48:53.831168-05	nndz-WkMrK3diNzlodz09	4513	t	\N	5	6	45.50		2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
324656	\N	Alison	Poteracki	4590	4349	2025-06-24 19:48:53.831168-05	nndz-WkM2eHliMzVqUT09	4513	t	\N	6	8	42.90		2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
324657	\N	Jackie	Scheer	4590	4349	2025-06-24 19:48:53.831168-05	nndz-WkM2eHliMzRoUT09	4513	t	\N	0	1	0.00		2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
324658	\N	Kathleen	Turnbull	4590	4349	2025-06-24 19:48:53.831168-05	nndz-WkM2eHliei9ndz09	4513	t	\N	8	7	53.30		2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
324659	\N	Joann	Williams	4590	4349	2025-06-24 19:48:53.831168-05	nndz-WkM2eHliMzRnUT09	4513	t	\N	2	4	33.30		2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
324660	\N	Natalie	Jeannin	4590	4349	2025-06-24 19:48:53.831168-05	nndz-WkM2eHliei9oUT09	4513	t	\N	3	3	50.00		2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
324661	\N	Kelly	Kenna	4590	4349	2025-06-24 19:48:53.831168-05	nndz-WlNlL3dyZjRnQT09	4513	t	\N	11	13	45.80		2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
324662	\N	Katie	Stritch	4590	4349	2025-06-24 19:48:53.831168-05	nndz-WlNlL3hyajhnQT09	4513	t	\N	6	2	75.00		2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
324663	\N	Abby	Wenstrup	4590	4349	2025-06-24 19:48:53.831168-05	nndz-WkM2eHliMzRoZz09	4513	t	\N	0	8	0.00		2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
324664	\N	Kristen	Lipsey	4608	4351	2025-06-24 19:48:53.831168-05	nndz-WkNDOHlMN3dnUT09	4513	t	\N	5	3	62.50	C	2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
324665	\N	Sara	Winstanley	4608	4351	2025-06-24 19:48:53.831168-05	nndz-WkNDL3dienhnZz09	4513	t	\N	3	4	42.90	CC	2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
324666	\N	Lindsey	Bruso	4608	4351	2025-06-24 19:48:53.831168-05	nndz-WkM2eHhMYjRqUT09	4513	t	\N	7	4	63.60		2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
324667	\N	Andrea	Patchin	4608	4351	2025-06-24 19:48:53.831168-05	nndz-WkNDOHlMNytoUT09	4513	t	\N	4	3	57.10		2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
324668	\N	Molly	Regan	4608	4351	2025-06-24 19:48:53.831168-05	nndz-WkNDOHlMejdoQT09	4513	t	\N	6	5	54.50		2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
324669	\N	Tasha	Vallace	4608	4351	2025-06-24 19:48:53.831168-05	nndz-WkNDOHlMejdnQT09	4513	t	\N	5	2	71.40		2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
324670	\N	Bridget	Kirkendall	4608	4351	2025-06-24 19:48:53.831168-05	nndz-WkNDOHlMejdnUT09	4513	t	\N	4	3	57.10		2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
324671	\N	Cathy	McCulloch	4608	4351	2025-06-24 19:48:53.831168-05	nndz-WkNDOHlMejRnZz09	4513	t	\N	2	5	28.60		2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
324672	\N	Chantal	Meier	4608	4351	2025-06-24 19:48:53.831168-05	nndz-WkNDOHlMNy9oZz09	4513	t	\N	6	5	54.50		2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
324673	\N	Catherine	Sullivan - MSC	4608	4351	2025-06-24 19:48:53.831168-05	nndz-WkNDOHlMejRoZz09	4513	t	\N	4	3	57.10		2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
324674	\N	Kristen	Bowie	4608	4352	2025-06-24 19:48:53.831168-05	nndz-WkM2eHhMYjdoUT09	4513	t	\N	4	3	57.10	C	2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
324675	\N	Sarah	O'Brien	4608	4352	2025-06-24 19:48:53.831168-05	nndz-WkNDOHlMYjRndz09	4513	t	\N	2	4	33.30	CC	2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
324676	\N	Nicole	Botsman	4608	4352	2025-06-24 19:48:53.831168-05	nndz-WkNHN3c3cndnQT09	4513	t	\N	6	3	66.70		2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
324677	\N	Allison	Elfman	4608	4352	2025-06-24 19:48:53.831168-05	nndz-WkNDOHlMZi9nUT09	4513	t	\N	2	5	28.60		2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
324678	\N	Jane	Hennessey	4608	4352	2025-06-24 19:48:53.831168-05	nndz-WkNDL3didjloZz09	4513	t	\N	5	6	45.50		2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
324679	\N	Jeanne	Kelso	4608	4352	2025-06-24 19:48:53.831168-05	nndz-WkNHNXlMLzloZz09	4513	t	\N	5	6	45.50		2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
324680	\N	Julia	Latsch	4608	4352	2025-06-24 19:48:53.831168-05	nndz-WkM2eHhMZitqQT09	4513	t	\N	10	8	55.60		2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
324681	\N	Katie	McCalla	4608	4352	2025-06-24 19:48:53.831168-05	nndz-WkNDL3diMytqUT09	4513	t	\N	6	0	100.00		2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
324682	\N	Monica	Thompson	4608	4352	2025-06-24 19:48:53.831168-05	nndz-WkNDOHlMNy9nZz09	4513	t	\N	2	5	28.60		2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
324683	\N	Julie	Adrianopoli	4608	4352	2025-06-24 19:48:53.831168-05	nndz-WkM2eHhMZitqUT09	4513	t	\N	8	4	66.70		2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
324684	\N	Michelle	Andrew	4608	4352	2025-06-24 19:48:53.831168-05	nndz-WkNDOHlMei9nZz09	4513	t	\N	4	6	40.00		2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
324685	\N	Holly	Patience	4611	4349	2025-06-24 19:48:53.831168-05	nndz-WkNDOHlMei9oQT09	4513	t	\N	1	7	12.50	C	2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
324686	\N	Susan	Doyle	4611	4349	2025-06-24 19:48:53.831168-05	nndz-WkNDOHlMejZndz09	4513	t	\N	5	1	83.30		2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
324687	\N	Sarah	Dwyer	4611	4349	2025-06-24 19:48:53.831168-05	nndz-WkNDOHlMejZnZz09	4513	t	\N	4	3	57.10		2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
324688	\N	Lindsay	Ferber	4611	4349	2025-06-24 19:48:53.831168-05	nndz-WkNDOHlMYnhqUT09	4513	t	\N	2	6	25.00		2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
324689	\N	Jen	Finger	4611	4349	2025-06-24 19:48:53.831168-05	nndz-WkNDOHlMejlqUT09	4513	t	\N	4	3	57.10		2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
324690	\N	Jennifer	Gilroy	4611	4349	2025-06-24 19:48:53.831168-05	nndz-WkNDOHlMejlnQT09	4513	t	\N	0	0	0.00		2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
324691	\N	Amy	Jones	4611	4349	2025-06-24 19:48:53.831168-05	nndz-WkNDL3diM3doZz09	4513	t	\N	0	0	0.00		2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
324692	\N	Mindy	Purcell	4611	4349	2025-06-24 19:48:53.831168-05	nndz-WkNDOHlMejhoZz09	4513	t	\N	0	0	0.00		2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
324693	\N	Colleen	Levitz	4611	4349	2025-06-24 19:48:53.831168-05	nndz-WkNDOHlMejZoZz09	4513	t	\N	0	0	0.00		2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
324694	\N	MJ	Murnane	4611	4349	2025-06-24 19:48:53.831168-05	nndz-WkNDOHlMejZodz09	4513	t	\N	0	0	0.00		2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
324695	\N	Carey	Gifford	4611	4349	2025-06-24 19:48:53.831168-05	nndz-WkNDOHlMejZqQT09	4513	t	\N	0	0	0.00		2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
324696	\N	Katie	Baisley	4611	4349	2025-06-24 19:48:53.831168-05	nndz-WkM2eHhMZnhodz09	4513	t	\N	0	0	0.00		2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
324697	\N	Jane	Hutson	4611	4349	2025-06-24 19:48:53.831168-05	nndz-WkNDOHlMaitoQT09	4513	t	\N	0	0	0.00		2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
324698	\N	Whitley	Herbert	4617	4349	2025-06-24 19:48:53.831168-05	nndz-WkMrNnc3dnhqQT09	4513	t	\N	6	1	85.70	C	2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
324699	\N	Avery	Keller	4617	4349	2025-06-24 19:48:53.831168-05	nndz-WkNDOHlMMzVoUT09	4513	t	\N	4	0	100.00	CC	2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
324700	\N	Tracy	Barrett	4617	4349	2025-06-24 19:48:53.831168-05	nndz-WkNDOHlMMzVqQT09	4513	t	\N	2	3	40.00		2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
324701	\N	Amy	Davidson	4617	4349	2025-06-24 19:48:53.831168-05	nndz-WkNDOHlMaitoUT09	4513	t	\N	2	3	40.00		2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
324702	\N	Diane	Grumhaus	4617	4349	2025-06-24 19:48:53.831168-05	nndz-WkNDOHlMMzVoQT09	4513	t	\N	1	3	25.00		2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
324703	\N	Katie	Hickey	4617	4349	2025-06-24 19:48:53.831168-05	nndz-WkNDOHlMM3dqQT09	4513	t	\N	0	4	0.00		2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
324704	\N	Cindy	Holman	4617	4349	2025-06-24 19:48:53.831168-05	nndz-WkNDOHlMbitnQT09	4513	t	\N	2	3	40.00		2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
324705	\N	Michele	Ihlanfeldt	4617	4349	2025-06-24 19:48:53.831168-05	nndz-WkNDOHlMMzVnQT09	4513	t	\N	1	4	20.00		2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
324706	\N	Sheila	Keil	4617	4349	2025-06-24 19:48:53.831168-05	nndz-WkNDOHlMai9qQT09	4513	t	\N	4	5	44.40		2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
324707	\N	Perry	Minter	4617	4349	2025-06-24 19:48:53.831168-05	nndz-WkM2eHhMYjdnUT09	4513	t	\N	6	1	85.70		2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
324708	\N	Mimi	Murley Doyle	4617	4349	2025-06-24 19:48:53.831168-05	nndz-WkNDL3diNzVoQT09	4513	t	\N	1	6	14.30		2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
324709	\N	Lucinda	Sheffield	4617	4349	2025-06-24 19:48:53.831168-05	nndz-WkNDOHlMendndz09	4513	t	\N	5	2	71.40		2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
324710	\N	Katie	Ford	4617	4349	2025-06-24 19:48:53.831168-05	nndz-WkNDOHlMMzVnUT09	4513	t	\N	0	0	0.00		2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
324711	\N	Grace	Gescheidle	4617	4349	2025-06-24 19:48:53.831168-05	nndz-WlNlN3lidjZoQT09	4513	t	\N	6	4	60.00		2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
324712	\N	Elinor	Jannotta	4617	4349	2025-06-24 19:48:53.831168-05	nndz-WkNDOHlMYjVoUT09	4513	t	\N	0	0	0.00		2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
324713	\N	Farley	Lansing	4617	4349	2025-06-24 19:48:53.831168-05	nndz-WkM2d3hMei9ndz09	4513	t	\N	0	0	0.00		2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
324714	\N	Lindsay	Bloom	4617	4349	2025-06-24 19:48:53.831168-05	nndz-WkNDL3diNzVodz09	4513	t	\N	7	2	77.80		2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
324715	\N	Emily	Krall	4617	4349	2025-06-24 19:48:53.831168-05	nndz-WkM2eHg3NzdoZz09	4513	t	\N	1	0	100.00		2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
324716	\N	Meredith	Sullivan	4617	4349	2025-06-24 19:48:53.831168-05	nndz-WkNDOHlMZndnUT09	4513	t	\N	5	3	62.50		2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
324717	\N	Erin	Trella	4638	4349	2025-06-24 19:48:53.831168-05	nndz-WkNDOHlMZjdoQT09	4513	t	\N	3	4	42.90	C	2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
324718	\N	Reagan	Knaus	4638	4349	2025-06-24 19:48:53.831168-05	nndz-WkNDOHlMcitoZz09	4513	t	\N	6	5	54.50	CC	2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
324719	\N	Melissa	Dakoff	4638	4349	2025-06-24 19:48:53.831168-05	nndz-WkM2eHg3N3dqUT09	4513	t	\N	5	4	55.60		2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
324720	\N	Stephanie	Dougherty	4638	4349	2025-06-24 19:48:53.831168-05	nndz-WkM2eHhMYndoQT09	4513	t	\N	3	10	23.10		2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
324721	\N	Becky	Gustafson	4638	4349	2025-06-24 19:48:53.831168-05	nndz-WkNDOHlMcitnZz09	4513	t	\N	1	5	16.70		2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
324722	\N	Bridget	Hughes	4638	4349	2025-06-24 19:48:53.831168-05	nndz-WkNDOHlMandqUT09	4513	t	\N	3	3	50.00		2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
324723	\N	Jennifer	Humphrey	4638	4349	2025-06-24 19:48:53.831168-05	nndz-WkM2eHhMYndodz09	4513	t	\N	3	5	37.50		2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
324724	\N	Liesel	Jankelowitz	4638	4349	2025-06-24 19:48:53.831168-05	nndz-WkM2eHhyditnQT09	4513	t	\N	7	2	77.80		2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
324725	\N	Kristin	Keevins	4638	4349	2025-06-24 19:48:53.831168-05	nndz-WkNDOHlMci9nUT09	4513	t	\N	2	4	33.30		2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
324726	\N	Casey	Pierson	4638	4349	2025-06-24 19:48:53.831168-05	nndz-WkM2eHhybjlndz09	4513	t	\N	8	3	72.70		2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
324727	\N	Dana	Schnurman	4638	4349	2025-06-24 19:48:53.831168-05	nndz-WkM2eHg3NzZoUT09	4513	t	\N	5	6	45.50		2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
324728	\N	Gina	Holton	4640	4349	2025-06-24 19:48:53.831168-05	nndz-WkNDOHlMYjRoZz09	4513	t	\N	7	3	70.00	C	2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
324729	\N	Alison	Olsen	4640	4349	2025-06-24 19:48:53.831168-05	nndz-WkNDL3diLzdnQT09	4513	t	\N	5	2	71.40	CC	2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
324730	\N	Jenny	Frentzel	4640	4349	2025-06-24 19:48:53.831168-05	nndz-WkNDOHlMdjVnQT09	4513	t	\N	3	4	42.90		2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
324731	\N	Meghan	Jenkins	4640	4349	2025-06-24 19:48:53.831168-05	nndz-WkNDOHlMYjRoQT09	4513	t	\N	6	5	54.50		2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
324732	\N	Maerry	Lee	4640	4349	2025-06-24 19:48:53.831168-05	nndz-WkM2eHhMYjRnUT09	4513	t	\N	3	0	100.00		2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
324733	\N	Tyra	Leonard	4640	4349	2025-06-24 19:48:53.831168-05	nndz-WkNDOHlMdjdoQT09	4513	t	\N	9	2	81.80		2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
324734	\N	Susan	Locke	4640	4349	2025-06-24 19:48:53.831168-05	nndz-WkNDOHlMbjRnZz09	4513	t	\N	8	4	66.70		2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
324735	\N	Mary	Jane Melgaard	4640	4349	2025-06-24 19:48:53.831168-05	nndz-WkNHNHlMLzRodz09	4513	t	\N	8	3	72.70		2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
324736	\N	Kim	Reynolds	4640	4349	2025-06-24 19:48:53.831168-05	nndz-WkNDOHlMdjRoZz09	4513	t	\N	1	7	12.50		2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
324737	\N	Debbie	Smith	4640	4349	2025-06-24 19:48:53.831168-05	nndz-WkNDOHlMajZoUT09	4513	t	\N	11	5	68.80		2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
324738	\N	Emily	Cittadine	4640	4349	2025-06-24 19:48:53.831168-05	nndz-WkM2eHhyZjloQT09	4513	t	\N	1	6	14.30		2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
324739	\N	Lea	Halvadia	4640	4349	2025-06-24 19:48:53.831168-05	nndz-WkNDL3dicitnZz09	4513	t	\N	6	2	75.00		2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
324740	\N	Nancy	Spring	4640	4349	2025-06-24 19:48:53.831168-05	nndz-WkNDOHlMdjRndz09	4513	t	\N	6	5	54.50		2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
324741	\N	Amy	Wolfe	4640	4349	2025-06-24 19:48:53.831168-05	nndz-WkNDOHlMLy9oZz09	4513	t	\N	5	2	71.40		2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
324742	\N	Jenny	Sollecito	4642	4349	2025-06-24 19:48:53.831168-05	nndz-WkNDOHlMLzhnQT09	4513	t	\N	0	4	0.00	C	2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
324743	\N	Lana	Good	4642	4349	2025-06-24 19:48:53.831168-05	nndz-WkNDOHlMYjdnUT09	4513	t	\N	1	7	12.50	CC	2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
324744	\N	Sharon	Bertrand	4642	4349	2025-06-24 19:48:53.831168-05	nndz-WkNDOHlMNy9qUT09	4513	t	\N	7	8	46.70		2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
324745	\N	Kathy	Covek	4642	4349	2025-06-24 19:48:53.831168-05	nndz-WkNDOHlMajlqQT09	4513	t	\N	7	1	87.50		2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
324746	\N	Alexandrea	Gjertsen	4642	4349	2025-06-24 19:48:53.831168-05	nndz-WkNDOHlMdjlnQT09	4513	t	\N	2	6	25.00		2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
324747	\N	Julie	Kimmel	4642	4349	2025-06-24 19:48:53.831168-05	nndz-WkNHNHlMM3dnQT09	4513	t	\N	0	4	0.00		2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
324748	\N	Mary	Kay Lauderback	4642	4349	2025-06-24 19:48:53.831168-05	nndz-WkNDOHlMLytnQT09	4513	t	\N	6	2	75.00		2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
324749	\N	Nell	O'Connor	4642	4349	2025-06-24 19:48:53.831168-05	nndz-WkNHNHlMLzRoUT09	4513	t	\N	0	0	0.00		2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
324750	\N	Whitney	O'Neill	4642	4349	2025-06-24 19:48:53.831168-05	nndz-WkNDOHlMbjdnQT09	4513	t	\N	1	6	14.30		2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
324751	\N	Lynne	Sakanich	4642	4349	2025-06-24 19:48:53.831168-05	nndz-WkNDOHlMNy9oUT09	4513	t	\N	4	8	33.30		2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
324752	\N	Debra	Warren	4642	4349	2025-06-24 19:48:53.831168-05	nndz-WkNDOHlMajlnUT09	4513	t	\N	6	5	54.50		2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
324753	\N	Liz	Krupkin	4642	4349	2025-06-24 19:48:53.831168-05	nndz-WkNHNHlMcjVoQT09	4513	t	\N	7	5	58.30		2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
324754	\N	Cathie	Flanagan	4642	4349	2025-06-24 19:48:53.831168-05	nndz-WkNDL3diejdnZz09	4513	t	\N	8	7	53.30		2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
324755	\N	Eleanor	Derleth	4580	4353	2025-06-24 19:48:53.831168-05	nndz-WkNDOHlMci9oQT09	4513	t	\N	3	3	50.00	C	2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
324756	\N	Julia	Jackoboice Miller	4580	4353	2025-06-24 19:48:53.831168-05	nndz-WkNDOHlMLzRoZz09	4513	t	\N	3	5	37.50	CC	2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
324757	\N	Sheila	Cavalaris	4580	4353	2025-06-24 19:48:53.831168-05	nndz-WkNDOHlMLzRndz09	4513	t	\N	3	4	42.90		2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
324758	\N	Anna	Kokke	4580	4353	2025-06-24 19:48:53.831168-05	nndz-WkNDOHlMYi9nZz09	4513	t	\N	5	3	62.50		2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
324759	\N	Patty	Lambropoulos	4580	4353	2025-06-24 19:48:53.831168-05	nndz-WkNDOHlMLzRodz09	4513	t	\N	6	2	75.00		2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
324760	\N	Beth	McKenna	4580	4353	2025-06-24 19:48:53.831168-05	nndz-WkNHNXlMMzloUT09	4513	t	\N	2	7	22.20		2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
324761	\N	Lisa	Murray	4580	4353	2025-06-24 19:48:53.831168-05	nndz-WkNDOHlMLzVqUT09	4513	t	\N	0	4	0.00		2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
324762	\N	Jillian	Segal	4580	4353	2025-06-24 19:48:53.831168-05	nndz-WkM2eHhMZjlnQT09	4513	t	\N	6	3	66.70		2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
324763	\N	Lois	Sheridan	4580	4353	2025-06-24 19:48:53.831168-05	nndz-WkNDOHlMcitnQT09	4513	t	\N	4	3	57.10		2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
324764	\N	Lydia	Barrett	4580	4353	2025-06-24 19:48:53.831168-05	nndz-WkM2eHliLzZodz09	4513	t	\N	4	5	44.40		2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
324765	\N	Dani	Blaser	4580	4353	2025-06-24 19:48:53.831168-05	nndz-WkMreHdici9qUT09	4513	t	\N	0	0	0.00		2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
324766	\N	Lydia	Hankins	4580	4353	2025-06-24 19:48:53.831168-05	nndz-WkM2eHhMZjlnUT09	4513	t	\N	0	0	0.00		2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
324767	\N	Katy	Kilborn	4580	4353	2025-06-24 19:48:53.831168-05	nndz-WkNDOHlMLzVnQT09	4513	t	\N	0	0	0.00		2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
324768	\N	Cyndi	Millspaugh	4580	4353	2025-06-24 19:48:53.831168-05	nndz-WkNHNXdydjlnQT09	4513	t	\N	0	0	0.00		2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
324769	\N	Gina	Stec	4580	4353	2025-06-24 19:48:53.831168-05	nndz-WkNDOHlMcnhndz09	4513	t	\N	0	0	0.00		2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
324770	\N	Gayle	Sullivan	4580	4353	2025-06-24 19:48:53.831168-05	nndz-WkNHNXdydjlnUT09	4513	t	\N	0	0	0.00		2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
324771	\N	Billie	Diamond	4580	4353	2025-06-24 19:48:53.831168-05	nndz-WkM2eHhyLzdnZz09	4513	t	\N	9	7	56.20		2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
324772	\N	Niki	VanVuren	4580	4353	2025-06-24 19:48:53.831168-05	nndz-WkNDL3diMzRqUT09	4513	t	\N	5	4	55.60		2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
324773	\N	Jenny	Zecevich	4580	4353	2025-06-24 19:48:53.831168-05	nndz-WkM2eHhyLzloQT09	4513	t	\N	8	6	57.10		2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
324774	\N	Stephanie	Pierce	4581	4353	2025-06-24 19:48:53.831168-05	nndz-WkM2eHliendndz09	4513	t	\N	0	0	0.00	C	2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
324775	\N	Michele	Muchmore	4581	4353	2025-06-24 19:48:53.831168-05	nndz-WkM2eHliendodz09	4513	t	\N	6	4	60.00	CC	2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
324776	\N	Betsy	Bush	4581	4353	2025-06-24 19:48:53.831168-05	nndz-WkM2eHlienhnZz09	4513	t	\N	3	4	42.90		2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
324777	\N	Erica	Carlson	4581	4353	2025-06-24 19:48:53.831168-05	nndz-WkMrNnc3ajVqUT09	4513	t	\N	2	2	50.00		2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
324778	\N	Ashley	Condon	4581	4353	2025-06-24 19:48:53.831168-05	nndz-WkM2eHlManhqUT09	4513	t	\N	8	0	100.00		2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
324779	\N	Didi	Foth	4581	4353	2025-06-24 19:48:53.831168-05	nndz-WkMrNnc3ajVoZz09	4513	t	\N	1	5	16.70		2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
324780	\N	Rachel	Harris	4581	4353	2025-06-24 19:48:53.831168-05	nndz-WkMrNnc3ajVnZz09	4513	t	\N	9	8	52.90		2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
324781	\N	Katherine	Mattison	4581	4353	2025-06-24 19:48:53.831168-05	nndz-WkMrNnc3Ny9oUT09	4513	t	\N	12	6	66.70		2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
324782	\N	Molly	McGinnis	4581	4353	2025-06-24 19:48:53.831168-05	nndz-WkM2eHliendoUT09	4513	t	\N	6	4	60.00		2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
324783	\N	Kristen	Rowley	4581	4353	2025-06-24 19:48:53.831168-05	nndz-WlNlN3hycjloZz09	4513	t	\N	4	2	66.70		2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
324784	\N	Barbara	Rueth	4581	4353	2025-06-24 19:48:53.831168-05	nndz-WkMrNnc3ajVoUT09	4513	t	\N	5	3	62.50		2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
324785	\N	Sarah	Schleinzer	4581	4353	2025-06-24 19:48:53.831168-05	nndz-WkM2eHliendnZz09	4513	t	\N	6	3	66.70		2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
324786	\N	Camey	Walker	4581	4353	2025-06-24 19:48:53.831168-05	nndz-WkMreHdMcitnUT09	4513	t	\N	1	1	50.00		2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
324787	\N	Amy	Hohulin	4581	4353	2025-06-24 19:48:53.831168-05	nndz-WlNhOXdiL3hndz09	4513	t	\N	5	4	55.60		2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
324788	\N	Mary	Mouw	4581	4353	2025-06-24 19:48:53.831168-05	nndz-WlNlL3lMeitnQT09	4513	t	\N	0	12	0.00		2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
324789	\N	Jodi	Norgaard	4581	4353	2025-06-24 19:48:53.831168-05	nndz-WkM2eHliendoZz09	4513	t	\N	9	1	90.00		2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
324790	\N	Nicole	Rutherford	4581	4353	2025-06-24 19:48:53.831168-05	nndz-WlNlOXhiZjlndz09	4513	t	\N	6	5	54.50		2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
324791	\N	Amanda	Southwell	4581	4353	2025-06-24 19:48:53.831168-05	nndz-WkM2eHliendqUT09	4513	t	\N	0	0	0.00		2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
324792	\N	Corey	Fennessy	4581	4353	2025-06-24 19:48:53.831168-05	nndz-WlNlL3lMejlqUT09	4513	t	\N	5	6	45.50		2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
324793	\N	Jessica	King	4581	4353	2025-06-24 19:48:53.831168-05	nndz-WlNlL3hicjlnZz09	4513	t	\N	3	0	100.00		2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
324794	\N	Hope	Rodine	4581	4353	2025-06-24 19:48:53.831168-05	nndz-WlNlL3hybjRodz09	4513	t	\N	3	2	60.00		2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
324795	\N	Cindy	West	4581	4353	2025-06-24 19:48:53.831168-05	nndz-WlNlOHhMNzZqUT09	4513	t	\N	0	1	0.00		2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
324796	\N	Kelly	Burgener	4599	4353	2025-06-24 19:48:53.831168-05	nndz-WkNDOHlMYjVnZz09	4513	t	\N	2	5	28.60	C	2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
324797	\N	Laurel	Bufe	4599	4353	2025-06-24 19:48:53.831168-05	nndz-WkNHNXdiYjlqUT09	4513	t	\N	1	5	16.70		2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
324798	\N	Brooke	Hubbuch	4599	4353	2025-06-24 19:48:53.831168-05	nndz-WkMrK3hici9oQT09	4513	t	\N	0	4	0.00		2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
324799	\N	Margaret	Kiela	4599	4353	2025-06-24 19:48:53.831168-05	nndz-WkNHNXdiYjlndz09	4513	t	\N	0	7	0.00		2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
324800	\N	Leslie	Leonardi	4599	4353	2025-06-24 19:48:53.831168-05	nndz-WkNHNXdiYjhodz09	4513	t	\N	7	7	50.00		2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
324801	\N	Kauri	McKendry	4599	4353	2025-06-24 19:48:53.831168-05	nndz-WkNHNHdiMy9qQT09	4513	t	\N	4	3	57.10		2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
324802	\N	Colleen	Moyer	4599	4353	2025-06-24 19:48:53.831168-05	nndz-WkNDOHlMditoQT09	4513	t	\N	0	1	0.00		2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
324803	\N	Gaby	Nichols	4599	4353	2025-06-24 19:48:53.831168-05	nndz-WkNDOHlMajVoUT09	4513	t	\N	1	4	20.00		2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
324804	\N	Elizabeth	O'Connor	4599	4353	2025-06-24 19:48:53.831168-05	nndz-WkNDOHlMZjRoQT09	4513	t	\N	7	7	50.00		2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
324805	\N	Lisa	Weber	4599	4353	2025-06-24 19:48:53.831168-05	nndz-WkNDL3diM3dodz09	4513	t	\N	0	7	0.00		2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
324806	\N	Emily	Woodruff	4599	4353	2025-06-24 19:48:53.831168-05	nndz-WkNHNXdiYjlnUT09	4513	t	\N	4	3	57.10		2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
324807	\N	Amy	McKernan	4599	4353	2025-06-24 19:48:53.831168-05	nndz-WkM2eHhMZjhodz09	4513	t	\N	1	1	50.00		2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
324808	\N	Carolyn	Wine	4618	4353	2025-06-24 19:48:53.831168-05	nndz-WkMrNnc3ajRndz09	4513	t	\N	0	7	0.00	C	2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
324809	\N	Kelly	Gust	4618	4353	2025-06-24 19:48:53.831168-05	nndz-WkNDOHlML3dnUT09	4513	t	\N	1	4	20.00	CC	2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
324810	\N	Kelly	Amelse	4618	4353	2025-06-24 19:48:53.831168-05	nndz-WkNDOHlMbitnUT09	4513	t	\N	1	9	10.00		2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
324811	\N	Linda	Buggy	4618	4353	2025-06-24 19:48:53.831168-05	nndz-WkM2d3g3bnhqQT09	4513	t	\N	10	7	58.80		2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
324812	\N	Linnea	Calabrese	4618	4353	2025-06-24 19:48:53.831168-05	nndz-WkNDOHlML3dqQT09	4513	t	\N	1	3	25.00		2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
324813	\N	Tina	DiLorenzo	4618	4353	2025-06-24 19:48:53.831168-05	nndz-WkNHNXdyNy9nZz09	4513	t	\N	7	6	53.80		2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
324814	\N	Denean	Faraci	4618	4353	2025-06-24 19:48:53.831168-05	nndz-WkNDOHlML3dnQT09	4513	t	\N	7	7	50.00		2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
324815	\N	Jennifer	Gallery	4618	4353	2025-06-24 19:48:53.831168-05	nndz-WkNDOHlML3hndz09	4513	t	\N	9	4	69.20		2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
324816	\N	Amanda	Miller	4618	4353	2025-06-24 19:48:53.831168-05	nndz-WkM2eHhycndqUT09	4513	t	\N	12	7	63.20		2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
324817	\N	Krista	Muir	4618	4353	2025-06-24 19:48:53.831168-05	nndz-WkM2eHhydjdndz09	4513	t	\N	3	6	33.30		2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
324818	\N	Mary	Ploen	4618	4353	2025-06-24 19:48:53.831168-05	nndz-WkNDOHlML3doQT09	4513	t	\N	0	0	0.00		2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
324819	\N	Elizabeth	Eshoo	4618	4353	2025-06-24 19:48:53.831168-05	nndz-WkNHNXdyNy9ndz09	4513	t	\N	1	9	10.00		2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
324820	\N	Mary	Hunt	4618	4353	2025-06-24 19:48:53.831168-05	nndz-WkM2eHhydjdnUT09	4513	t	\N	8	5	61.50		2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
324821	\N	Moira	Lisowski	4618	4353	2025-06-24 19:48:53.831168-05	nndz-WkM2eHhydjdnQT09	4513	t	\N	3	2	60.00		2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
324822	\N	Eleni	Patel	4618	4353	2025-06-24 19:48:53.831168-05	nndz-WkM2eHg3ai9odz09	4513	t	\N	5	3	62.50		2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
324823	\N	Nadine	Sir	4618	4353	2025-06-24 19:48:53.831168-05	nndz-WkNDL3diNzRoQT09	4513	t	\N	4	3	57.10		2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
324824	\N	Amy	Paris	4624	4353	2025-06-24 19:48:53.831168-05	nndz-WkNDOHlMZndndz09	4513	t	\N	4	8	33.30	C	2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
324825	\N	Aubrey	Keith	4624	4353	2025-06-24 19:48:53.831168-05	nndz-WlNlN3diLzRqUT09	4513	t	\N	5	7	41.70	CC	2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
324826	\N	Kathleen	Brennan	4624	4353	2025-06-24 19:48:53.831168-05	nndz-WkNDOHlMbjdnZz09	4513	t	\N	3	5	37.50		2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
324827	\N	Katie	Brunick	4624	4353	2025-06-24 19:48:53.831168-05	nndz-WkM2eHhMYi9oZz09	4513	t	\N	2	5	28.60		2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
324828	\N	Erin	Eberle	4624	4353	2025-06-24 19:48:53.831168-05	nndz-WkM2eHhMYi9nUT09	4513	t	\N	2	6	25.00		2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
324829	\N	Louise	Flagg	4624	4353	2025-06-24 19:48:53.831168-05	nndz-WkM2eHhMYi9nZz09	4513	t	\N	5	3	62.50		2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
324830	\N	Rose	Ann Greco	4624	4353	2025-06-24 19:48:53.831168-05	nndz-WlNlN3diLzRnZz09	4513	t	\N	9	2	81.80		2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
324831	\N	Karen	Hunter	4624	4353	2025-06-24 19:48:53.831168-05	nndz-WkM2eHhMYitodz09	4513	t	\N	4	2	66.70		2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
324832	\N	Kelly	Owens	4624	4353	2025-06-24 19:48:53.831168-05	nndz-WlNlN3diLzRndz09	4513	t	\N	7	7	50.00		2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
324833	\N	Kayte	Sleep	4624	4353	2025-06-24 19:48:53.831168-05	nndz-WlNlN3c3Mzdodz09	4513	t	\N	8	3	72.70		2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
324834	\N	Robin	Behre	4624	4353	2025-06-24 19:48:53.831168-05	nndz-WlNlN3c3MzRnQT09	4513	t	\N	0	0	0.00		2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
324835	\N	Kim	Hoyt	4624	4353	2025-06-24 19:48:53.831168-05	nndz-WlNhL3dyN3dodz09	4513	t	\N	1	3	25.00		2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
324836	\N	Karen	Judy-Foley	4624	4353	2025-06-24 19:48:53.831168-05	nndz-WkM2eHhMYitoZz09	4513	t	\N	3	1	75.00		2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
324837	\N	Dina	Mansour	4624	4353	2025-06-24 19:48:53.831168-05	nndz-WkM2eHhMYitnUT09	4513	t	\N	0	0	0.00		2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
324838	\N	Alexis	Hiller	4624	4353	2025-06-24 19:48:53.831168-05	nndz-WlNhK3dyajhnZz09	4513	t	\N	0	2	0.00		2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
324839	\N	Tricia	Cox	4631	4353	2025-06-24 19:48:53.831168-05	nndz-WkNDOHlMMy9oUT09	4513	t	\N	3	1	75.00	C	2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
324840	\N	Ashley	Netzky	4631	4353	2025-06-24 19:48:53.831168-05	nndz-WkNDOHlMai9ndz09	4513	t	\N	2	2	50.00	CC	2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
324841	\N	Elizabeth	Denison	4631	4353	2025-06-24 19:48:53.831168-05	nndz-WkMreHlicjlqUT09	4513	t	\N	2	6	25.00		2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
324842	\N	Jacquelynn	Gordon	4631	4353	2025-06-24 19:48:53.831168-05	nndz-WkNDOHlMMy9nQT09	4513	t	\N	3	3	50.00		2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
324843	\N	Jacqueline	Griesdorn	4631	4353	2025-06-24 19:48:53.831168-05	nndz-WkNDL3diN3dndz09	4513	t	\N	2	3	40.00		2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
324844	\N	Barb	Hearn	4631	4353	2025-06-24 19:48:53.831168-05	nndz-WkNHNXhiNzVnQT09	4513	t	\N	5	2	71.40		2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
324845	\N	Eileen	Herber	4631	4353	2025-06-24 19:48:53.831168-05	nndz-WkMrN3dyYjVqQT09	4513	t	\N	4	5	44.40		2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
324846	\N	Beth	Hermann	4631	4353	2025-06-24 19:48:53.831168-05	nndz-WkNDOHlMdjRnQT09	4513	t	\N	0	0	0.00		2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
324847	\N	Tara	Marsh	4631	4353	2025-06-24 19:48:53.831168-05	nndz-WkNDOHlManhqUT09	4513	t	\N	1	3	25.00		2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
324848	\N	Sally	McPherrin	4631	4353	2025-06-24 19:48:53.831168-05	nndz-WkNDOHlManhndz09	4513	t	\N	3	1	75.00		2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
324849	\N	Emily	Putze	4631	4353	2025-06-24 19:48:53.831168-05	nndz-WkMrN3dybndoQT09	4513	t	\N	6	2	75.00		2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
324850	\N	Barb	Sessions	4631	4353	2025-06-24 19:48:53.831168-05	nndz-WkNDOHlMMzlqQT09	4513	t	\N	0	1	0.00		2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
324851	\N	susan	white	4631	4353	2025-06-24 19:48:53.831168-05	nndz-WkNDOHlMYjVodz09	4513	t	\N	4	3	57.10		2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
324852	\N	Laurie	Yorke	4631	4353	2025-06-24 19:48:53.831168-05	nndz-WkNDOHlMdjRoUT09	4513	t	\N	1	5	16.70		2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
324853	\N	Barbara	Potter	4631	4353	2025-06-24 19:48:53.831168-05	nndz-WkNDOHlMMy9oQT09	4513	t	\N	0	0	0.00		2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
324854	\N	Michelle	Cullen	4635	4353	2025-06-24 19:48:53.831168-05	nndz-WkNDL3dicjdnUT09	4513	t	\N	1	6	14.30	C	2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
324855	\N	Kelly	Sweat	4635	4353	2025-06-24 19:48:53.831168-05	nndz-WkNDOHlMajloUT09	4513	t	\N	3	4	42.90	CC	2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
324856	\N	Rosa	Broseman	4635	4353	2025-06-24 19:48:53.831168-05	nndz-WkNDOHlMM3hqUT09	4513	t	\N	3	3	50.00		2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
324857	\N	Sally	Conley	4635	4353	2025-06-24 19:48:53.831168-05	nndz-WkNDOHlMM3hnQT09	4513	t	\N	5	2	71.40		2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
324858	\N	Nicole	Hayek	4635	4353	2025-06-24 19:48:53.831168-05	nndz-WkNDL3diNytqUT09	4513	t	\N	4	3	57.10		2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
324859	\N	Katie	Hielscher	4635	4353	2025-06-24 19:48:53.831168-05	nndz-WkNDeHdiL3hoQT09	4513	t	\N	5	0	100.00		2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
324860	\N	Aimee	Paracchini	4635	4353	2025-06-24 19:48:53.831168-05	nndz-WkNDOHlMM3hnUT09	4513	t	\N	4	2	66.70		2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
324861	\N	Laurie	Schachman	4635	4353	2025-06-24 19:48:53.831168-05	nndz-WkM2eHg3LzZqQT09	4513	t	\N	2	5	28.60		2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
324862	\N	Liz	Smylie	4635	4353	2025-06-24 19:48:53.831168-05	nndz-WkNDL3dicjdoZz09	4513	t	\N	11	9	55.00		2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
324863	\N	Kristi	Snyderman	4635	4353	2025-06-24 19:48:53.831168-05	nndz-WkNDOHlMajloZz09	4513	t	\N	3	3	50.00		2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
324864	\N	Amy	Sullivan	4635	4353	2025-06-24 19:48:53.831168-05	nndz-WkM2eHhMZjhqQT09	4513	t	\N	5	6	45.50		2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
324865	\N	Susan	Fraser	4635	4353	2025-06-24 19:48:53.831168-05	nndz-WkNDOHlMMzhnUT09	4513	t	\N	0	2	0.00		2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
324866	\N	Tracy	Hedstrom	4635	4353	2025-06-24 19:48:53.831168-05	nndz-WkNDOHlMMzhqUT09	4513	t	\N	0	2	0.00		2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
324867	\N	Leanne	Kurtzweil	4639	4353	2025-06-24 19:48:53.831168-05	nndz-WkM2eHg3NzZoQT09	4513	t	\N	4	5	44.40	C	2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
324868	\N	Sarah	Pieracci	4639	4353	2025-06-24 19:48:53.831168-05	nndz-WkNDOHlMbjVqQT09	4513	t	\N	5	2	71.40	CC	2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
324869	\N	Julie	Ball	4639	4353	2025-06-24 19:48:53.831168-05	nndz-WkM2eHhyYi9odz09	4513	t	\N	7	3	70.00		2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
324870	\N	Kerry	Ehlinger	4639	4353	2025-06-24 19:48:53.831168-05	nndz-WkNDOHlMdjVoUT09	4513	t	\N	4	4	50.00		2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
324871	\N	Trish	Herakovich	4639	4353	2025-06-24 19:48:53.831168-05	nndz-WkNDL3diejdnQT09	4513	t	\N	4	4	50.00		2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
324872	\N	Megan	Leadbetter	4639	4353	2025-06-24 19:48:53.831168-05	nndz-WkNDL3diN3dqUT09	4513	t	\N	6	1	85.70		2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
324873	\N	Tammy	Lundal	4639	4353	2025-06-24 19:48:53.831168-05	nndz-WkMrNnc3ditnZz09	4513	t	\N	5	5	50.00		2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
324874	\N	Emily	McCall	4639	4353	2025-06-24 19:48:53.831168-05	nndz-WkNDOHlMcndnZz09	4513	t	\N	4	2	66.70		2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
324875	\N	Amy	Persohn	4639	4353	2025-06-24 19:48:53.831168-05	nndz-WkNDOHlMZnhnQT09	4513	t	\N	5	3	62.50		2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
324876	\N	Nahrin	Marino	4639	4353	2025-06-24 19:48:53.831168-05	nndz-WkM2eHhyYjZnZz09	4513	t	\N	3	2	60.00		2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
324877	\N	Shay	Cwick	4639	4353	2025-06-24 19:48:53.831168-05	nndz-WkM2eHhyYnhnZz09	4513	t	\N	8	4	66.70		2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
324878	\N	Cynthia	Reeder	4639	4353	2025-06-24 19:48:53.831168-05	nndz-WkM2eHg3LzlnUT09	4513	t	\N	4	6	40.00		2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
324879	\N	Nora	Waryas	4639	4353	2025-06-24 19:48:53.831168-05	nndz-WkM2eHhyYjZoQT09	4513	t	\N	8	5	61.50		2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
324880	\N	Amy	Wolfe	4640	4353	2025-06-24 19:48:53.831168-05	nndz-WkNDOHlMLy9oZz09	4513	t	\N	5	2	71.40	C	2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
324881	\N	Nancy	Spring	4640	4353	2025-06-24 19:48:53.831168-05	nndz-WkNDOHlMdjRndz09	4513	t	\N	6	5	54.50	CC	2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
324882	\N	Abby	Burtelow	4640	4353	2025-06-24 19:48:53.831168-05	nndz-WkNDOHlMditodz09	4513	t	\N	7	5	58.30		2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
324883	\N	Heidi	Carey	4640	4353	2025-06-24 19:48:53.831168-05	nndz-WkNDL3dicndqQT09	4513	t	\N	5	1	83.30		2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
324884	\N	Lynn	Chookaszian	4640	4353	2025-06-24 19:48:53.831168-05	nndz-WkNDOHlMbjRndz09	4513	t	\N	2	5	28.60		2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
324885	\N	Tracey	Fitzgerald	4640	4353	2025-06-24 19:48:53.831168-05	nndz-WkNDL3dicitoQT09	4513	t	\N	2	5	28.60		2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
324886	\N	Nicole	Mooney	4640	4353	2025-06-24 19:48:53.831168-05	nndz-WkNDL3diLzZodz09	4513	t	\N	4	3	57.10		2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
324887	\N	Mary	Catherine Mortell	4640	4353	2025-06-24 19:48:53.831168-05	nndz-WkNDL3diLzdoQT09	4513	t	\N	4	4	50.00		2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
324888	\N	Kim	Shea	4640	4353	2025-06-24 19:48:53.831168-05	nndz-WkNHNXc3ci9oQT09	4513	t	\N	6	4	60.00		2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
324889	\N	Molly	Weinlader	4640	4353	2025-06-24 19:48:53.831168-05	nndz-WkNHNXc3ci9ndz09	4513	t	\N	6	1	85.70		2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
324890	\N	Kelly	Hudson	4640	4353	2025-06-24 19:48:53.831168-05	nndz-WkNDOHlMdjVqQT09	4513	t	\N	3	4	42.90		2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
324891	\N	Allison	Steinback	4640	4353	2025-06-24 19:48:53.831168-05	nndz-WkM2eHhyZjlqQT09	4513	t	\N	4	5	44.40		2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
324892	\N	Kelli	Handel	4642	4353	2025-06-24 19:48:53.831168-05	nndz-WkNHNXliL3hoQT09	4513	t	\N	1	7	12.50	C	2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
324893	\N	Katie	O'Connor	4642	4353	2025-06-24 19:48:53.831168-05	nndz-WkM2eHhMZndndz09	4513	t	\N	4	7	36.40	CC	2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
324894	\N	Sue	Davis	4642	4353	2025-06-24 19:48:53.831168-05	nndz-WkNDOHlMMzloQT09	4513	t	\N	0	5	0.00		2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
324895	\N	Laura	Feldman	4642	4353	2025-06-24 19:48:53.831168-05	nndz-WkNDOHlMMzRnZz09	4513	t	\N	1	5	16.70		2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
324896	\N	Josie	Fritz	4642	4353	2025-06-24 19:48:53.831168-05	nndz-WkMrK3lMLzVnQT09	4513	t	\N	9	2	81.80		2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
324897	\N	Jamie	Peisel	4642	4353	2025-06-24 19:48:53.831168-05	nndz-WlNlN3diLytnQT09	4513	t	\N	10	6	62.50		2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
324898	\N	Mazy	Rhuberg	4642	4353	2025-06-24 19:48:53.831168-05	nndz-WlNlNnliejdqQT09	4513	t	\N	0	0	0.00		2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
324899	\N	Teri	Rosenberg	4642	4353	2025-06-24 19:48:53.831168-05	nndz-WkNDOHlMMzZndz09	4513	t	\N	2	7	22.20		2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
324900	\N	Moira	Stein	4642	4353	2025-06-24 19:48:53.831168-05	nndz-WkNHNHlMLzVqUT09	4513	t	\N	9	3	75.00		2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
324901	\N	Fontaine	Stellas	4642	4353	2025-06-24 19:48:53.831168-05	nndz-WkNDOHlManhnUT09	4513	t	\N	1	2	33.30		2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
324902	\N	Cathie	Flanagan	4642	4353	2025-06-24 19:48:53.831168-05	nndz-WkNDL3diejdnZz09	4513	t	\N	8	7	53.30		2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
324903	\N	Lauren	Kane	4642	4353	2025-06-24 19:48:53.831168-05	nndz-WkM2eHhMYi9oUT09	4513	t	\N	8	4	66.70		2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
324904	\N	Liz	Krupkin	4642	4353	2025-06-24 19:48:53.831168-05	nndz-WkNHNHlMcjVoQT09	4513	t	\N	7	5	58.30		2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
324905	\N	Elizabeth	Fox	4571	4355	2025-06-24 19:48:53.831168-05	nndz-WkNHNXdyejRndz09	4513	t	\N	6	2	75.00	C	2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
324906	\N	Rebecca	Gilberg	4571	4355	2025-06-24 19:48:53.831168-05	nndz-WkM2eHhMZi9nQT09	4513	t	\N	10	1	90.90	CC	2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
324907	\N	Linsey	Cohen	4571	4355	2025-06-24 19:48:53.831168-05	nndz-WkNHNXdyejRnUT09	4513	t	\N	4	3	57.10		2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
324908	\N	Jamie	Mazursky	4571	4355	2025-06-24 19:48:53.831168-05	nndz-WkNDOHlMN3hnUT09	4513	t	\N	5	2	71.40		2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
324909	\N	Lisa	Mintzer	4571	4355	2025-06-24 19:48:53.831168-05	nndz-WkNHNXdMZjlqQT09	4513	t	\N	6	2	75.00		2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
324910	\N	Melissa	Pessis	4571	4355	2025-06-24 19:48:53.831168-05	nndz-WkM2eHhMZi9qUT09	4513	t	\N	8	1	88.90		2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
324911	\N	Margaux	Sayer	4571	4355	2025-06-24 19:48:53.831168-05	nndz-WkNDL3diMzdnQT09	4513	t	\N	7	0	100.00		2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
324912	\N	Marnie	Sperling	4571	4355	2025-06-24 19:48:53.831168-05	nndz-WkNHNXdyejdoUT09	4513	t	\N	4	3	57.10		2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
324913	\N	Taryn	Stein	4571	4355	2025-06-24 19:48:53.831168-05	nndz-WkNDL3diMzdqQT09	4513	t	\N	9	2	81.80		2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
324914	\N	Staci	Teufel	4571	4355	2025-06-24 19:48:53.831168-05	nndz-WkM2eHg3NytoUT09	4513	t	\N	8	0	100.00		2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
324915	\N	Anne	Theophilos	4589	4355	2025-06-24 19:48:53.831168-05	nndz-WkM2eHliMzdqUT09	4513	t	\N	0	7	0.00	C	2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
324916	\N	Maggie	Gerth	4589	4355	2025-06-24 19:48:53.831168-05	nndz-WkM2eHliMzRqQT09	4513	t	\N	0	6	0.00	CC	2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
324917	\N	Elena	Baroni	4589	4355	2025-06-24 19:48:53.831168-05	nndz-WkM2eHliMzRnQT09	4513	t	\N	3	5	37.50		2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
324918	\N	Patti	Coyle	4589	4355	2025-06-24 19:48:53.831168-05	nndz-WkM2eHliMzRndz09	4513	t	\N	2	5	28.60		2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
324919	\N	Beth	George	4589	4355	2025-06-24 19:48:53.831168-05	nndz-WkM2eHliMzRnZz09	4513	t	\N	0	6	0.00		2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
324920	\N	Margaret	Hawn	4589	4355	2025-06-24 19:48:53.831168-05	nndz-WkM2eHliMzdoQT09	4513	t	\N	1	3	25.00		2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
324921	\N	Molly	Hughes	4589	4355	2025-06-24 19:48:53.831168-05	nndz-WkM2eHliMzdodz09	4513	t	\N	5	2	71.40		2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
324922	\N	Ashley	Killpack	4589	4355	2025-06-24 19:48:53.831168-05	nndz-WkM2eHliMzdoZz09	4513	t	\N	3	2	60.00		2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
324923	\N	Betsy	Moran	4589	4355	2025-06-24 19:48:53.831168-05	nndz-WkM2eHliMzdnUT09	4513	t	\N	0	6	0.00		2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
324924	\N	Sarah	Opler	4589	4355	2025-06-24 19:48:53.831168-05	nndz-WkM2eHliMzdndz09	4513	t	\N	3	0	100.00		2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
324925	\N	Nora	Tonn	4589	4355	2025-06-24 19:48:53.831168-05	nndz-WkM2eHliMzZoUT09	4513	t	\N	2	5	28.60		2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
324926	\N	Diana	Viravec	4589	4355	2025-06-24 19:48:53.831168-05	nndz-WlNlNndyZi9nZz09	4513	t	\N	1	9	10.00		2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
324927	\N	Sarah	Chase	4589	4355	2025-06-24 19:48:53.831168-05	nndz-WkMrNnc3dndqUT09	4513	t	\N	1	5	16.70		2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
324928	\N	Kathryn	Crist	4589	4355	2025-06-24 19:48:53.831168-05	nndz-WlNlOXdMZjdnZz09	4513	t	\N	0	0	0.00		2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
324929	\N	Meagan	Daly	4589	4355	2025-06-24 19:48:53.831168-05	nndz-WlNlOXdMZjdqUT09	4513	t	\N	0	0	0.00		2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
324930	\N	Lael	Falls	4589	4355	2025-06-24 19:48:53.831168-05	nndz-WlNlOXdMZjdqQT09	4513	t	\N	0	0	0.00		2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
324931	\N	Melissa	Goebel	4589	4355	2025-06-24 19:48:53.831168-05	nndz-WlNlOXdMZjZoUT09	4513	t	\N	0	0	0.00		2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
324932	\N	Therese	Hernandez	4589	4355	2025-06-24 19:48:53.831168-05	nndz-WlNlOXdMZjZoQT09	4513	t	\N	0	0	0.00		2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
324933	\N	Brittany	Jelinek	4589	4355	2025-06-24 19:48:53.831168-05	nndz-WlNlOXdMZjRnUT09	4513	t	\N	0	0	0.00		2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
324934	\N	Sheryl	Kern	4589	4355	2025-06-24 19:48:53.831168-05	nndz-WlNlOXdMZjZodz09	4513	t	\N	0	0	0.00		2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
324935	\N	Zara	Kinsella	4589	4355	2025-06-24 19:48:53.831168-05	nndz-WlNlOXdMZjZoZz09	4513	t	\N	0	0	0.00		2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
324936	\N	Allison	Knuepfer	4589	4355	2025-06-24 19:48:53.831168-05	nndz-WlNlOXdMZjRnQT09	4513	t	\N	0	0	0.00		2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
324937	\N	Patty	Kuzmic	4589	4355	2025-06-24 19:48:53.831168-05	nndz-WlNlOXdMZjZnUT09	4513	t	\N	0	0	0.00		2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
324938	\N	Sue	Lasek	4589	4355	2025-06-24 19:48:53.831168-05	nndz-WkMrNnc3dndqQT09	4513	t	\N	0	0	0.00		2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
324939	\N	Jodi	Leonard	4589	4355	2025-06-24 19:48:53.831168-05	nndz-WlNlOXdMZjRndz09	4513	t	\N	0	0	0.00		2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
324940	\N	Mary	Lyne	4589	4355	2025-06-24 19:48:53.831168-05	nndz-WlNlOXdMZjRnZz09	4513	t	\N	0	0	0.00		2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
324941	\N	Becky	Mavon	4589	4355	2025-06-24 19:48:53.831168-05	nndz-WlNlOXdMZjRqUT09	4513	t	\N	0	0	0.00		2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
324942	\N	Sheila	Moser	4589	4355	2025-06-24 19:48:53.831168-05	nndz-WlNlOXdMZjRqQT09	4513	t	\N	0	0	0.00		2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
324943	\N	Aly	Murphy	4589	4355	2025-06-24 19:48:53.831168-05	nndz-WlNlOXdMZjdoUT09	4513	t	\N	0	0	0.00		2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
324944	\N	Katelin	Nelson	4589	4355	2025-06-24 19:48:53.831168-05	nndz-WlNlOXdMZjdodz09	4513	t	\N	0	0	0.00		2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
324945	\N	Carol	Park	4589	4355	2025-06-24 19:48:53.831168-05	nndz-WkM2eHliMzdnZz09	4513	t	\N	0	0	0.00		2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
324946	\N	Kerstin	Regnery	4589	4355	2025-06-24 19:48:53.831168-05	nndz-WlNlOXdMZjdoZz09	4513	t	\N	0	0	0.00		2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
324947	\N	Lauren	Rock	4589	4355	2025-06-24 19:48:53.831168-05	nndz-WlNlOXdMZjdnUT09	4513	t	\N	0	0	0.00		2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
324948	\N	Mallory	Sitkowski	4589	4355	2025-06-24 19:48:53.831168-05	nndz-WlNlOXdMZjZndz09	4513	t	\N	0	0	0.00		2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
324949	\N	Jamie	Weibel	4589	4355	2025-06-24 19:48:53.831168-05	nndz-WlNlOXdMZjZnZz09	4513	t	\N	0	0	0.00		2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
324950	\N	Catherine	Ann Welch	4589	4355	2025-06-24 19:48:53.831168-05	nndz-WlNlOXdMZjdnQT09	4513	t	\N	0	0	0.00		2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
324951	\N	Anne	Stewart	4595	4355	2025-06-24 19:48:53.831168-05	nndz-WkNDOHlMYndndz09	4513	t	\N	1	1	50.00	C	2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
324952	\N	Courtney	Trombley	4595	4355	2025-06-24 19:48:53.831168-05	nndz-WkNDOHlMYndnZz09	4513	t	\N	6	1	85.70	CC	2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
324953	\N	Mary	Bires	4595	4355	2025-06-24 19:48:53.831168-05	nndz-WkNDOHlMYjdnQT09	4513	t	\N	4	1	80.00		2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
324954	\N	Julie	Carlson	4595	4355	2025-06-24 19:48:53.831168-05	nndz-WkNDOHlMajZnQT09	4513	t	\N	0	4	0.00		2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
324955	\N	Lindsey	Chabraja	4595	4355	2025-06-24 19:48:53.831168-05	nndz-WkNDOHlMYjdndz09	4513	t	\N	4	1	80.00		2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
324956	\N	Kim	Gambit	4595	4355	2025-06-24 19:48:53.831168-05	nndz-WkNDOHlMdjdndz09	4513	t	\N	4	4	50.00		2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
324957	\N	Linda	Ganshirt	4595	4355	2025-06-24 19:48:53.831168-05	nndz-WkNDOHlMdjZoQT09	4513	t	\N	0	5	0.00		2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
324958	\N	Brooke	Garrigan	4595	4355	2025-06-24 19:48:53.831168-05	nndz-WkNDOHlMdjdodz09	4513	t	\N	1	6	14.30		2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
324959	\N	Nicole	Graham	4595	4355	2025-06-24 19:48:53.831168-05	nndz-WkM2eHg3N3hodz09	4513	t	\N	3	4	42.90		2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
324960	\N	Kathy	Lipp	4595	4355	2025-06-24 19:48:53.831168-05	nndz-WkNDOHlMdjZoUT09	4513	t	\N	2	3	40.00		2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
324961	\N	Stacey	Marquis	4595	4355	2025-06-24 19:48:53.831168-05	nndz-WkNDOHlMdjdnZz09	4513	t	\N	4	4	50.00		2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
324962	\N	Vicki	Pasquesi	4595	4355	2025-06-24 19:48:53.831168-05	nndz-WkNDOHlMdjdoZz09	4513	t	\N	5	2	71.40		2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
324963	\N	Liz	Alkon	4595	4355	2025-06-24 19:48:53.831168-05	nndz-WkM2eHg3ejZqUT09	4513	t	\N	6	1	85.70		2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
324964	\N	Kiersten	Litzsinger	4595	4355	2025-06-24 19:48:53.831168-05	nndz-WkNHNXdMM3dqQT09	4513	t	\N	6	1	85.70		2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
324965	\N	Nisha	York	4595	4355	2025-06-24 19:48:53.831168-05	nndz-WkNHN3diMzdnQT09	4513	t	\N	7	1	87.50		2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
324966	\N	Michelle	Newman	4600	4355	2025-06-24 19:48:53.831168-05	nndz-WkM2d3dMcjhqUT09	4513	t	\N	3	3	50.00	C	2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
324967	\N	Karin	Longeway	4600	4355	2025-06-24 19:48:53.831168-05	nndz-WkNDOHlMLytnZz09	4513	t	\N	5	5	50.00	CC	2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
324968	\N	Carrie	Adolph	4600	4355	2025-06-24 19:48:53.831168-05	nndz-WkNDOHlMZjlodz09	4513	t	\N	13	4	76.50		2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
324969	\N	Carolyn	DeLuca	4600	4355	2025-06-24 19:48:53.831168-05	nndz-WkNDOHlMZjloZz09	4513	t	\N	5	3	62.50		2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
324970	\N	Amy	Gordy	4600	4355	2025-06-24 19:48:53.831168-05	nndz-WkM2eHhyMzRndz09	4513	t	\N	10	6	62.50		2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
324971	\N	Jenna	Long	4600	4355	2025-06-24 19:48:53.831168-05	nndz-WkM2eHhyMzRqUT09	4513	t	\N	8	5	61.50		2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
324972	\N	Emily	Malone	4600	4355	2025-06-24 19:48:53.831168-05	nndz-WkNDOHlMZjlndz09	4513	t	\N	6	2	75.00		2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
324973	\N	Amy	Mynhier	4600	4355	2025-06-24 19:48:53.831168-05	nndz-WkM2eHhyMzZoUT09	4513	t	\N	7	1	87.50		2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
324974	\N	Natalie	Reinkemeyer	4600	4355	2025-06-24 19:48:53.831168-05	nndz-WkNDOHlMLy9qUT09	4513	t	\N	5	2	71.40		2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
324975	\N	Suzanne	Bentley	4600	4355	2025-06-24 19:48:53.831168-05	nndz-WkNDOHlML3hoQT09	4513	t	\N	0	0	0.00		2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
324976	\N	Lorraine	Freedman	4600	4355	2025-06-24 19:48:53.831168-05	nndz-WkNDOHlMLytodz09	4513	t	\N	3	1	75.00		2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
324977	\N	Caryllon	Huggins	4600	4355	2025-06-24 19:48:53.831168-05	nndz-WkNDOHlML3hqUT09	4513	t	\N	0	0	0.00		2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
324978	\N	Kelly	Brincat	4600	4355	2025-06-24 19:48:53.831168-05	nndz-WkNDOHlMZjdoZz09	4513	t	\N	4	4	50.00		2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
324979	\N	Anne	Moebius	4600	4355	2025-06-24 19:48:53.831168-05	nndz-WkNDL3dienhoQT09	4513	t	\N	7	4	63.60		2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
324980	\N	Jenna	Zilka	4600	4355	2025-06-24 19:48:53.831168-05	nndz-WkM2eHhyMzdoQT09	4513	t	\N	3	4	42.90		2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
324981	\N	Sandy	Walker	4611	4355	2025-06-24 19:48:53.831168-05	nndz-WkNDOHlMejlqQT09	4513	t	\N	1	4	20.00	C	2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
324982	\N	Susan	Anthony	4611	4355	2025-06-24 19:48:53.831168-05	nndz-WkNDOHlMeitnZz09	4513	t	\N	0	8	0.00		2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
324983	\N	Erin	Burke	4611	4355	2025-06-24 19:48:53.831168-05	nndz-WkNDOHlMYnhnUT09	4513	t	\N	1	7	12.50		2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
324984	\N	Jodi	Daul	4611	4355	2025-06-24 19:48:53.831168-05	nndz-WkNDOHlMbjVnZz09	4513	t	\N	0	8	0.00		2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
324985	\N	Santhe	Phillips	4611	4355	2025-06-24 19:48:53.831168-05	nndz-WkNDOHlMejhndz09	4513	t	\N	0	0	0.00		2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
324986	\N	Amanda	Sargent	4611	4355	2025-06-24 19:48:53.831168-05	nndz-WkNDOHlMYndnUT09	4513	t	\N	1	5	16.70		2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
324987	\N	Jody	Savino	4611	4355	2025-06-24 19:48:53.831168-05	nndz-WkNDOHlMejloUT09	4513	t	\N	0	2	0.00		2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
324988	\N	Catherine	Stevens	4611	4355	2025-06-24 19:48:53.831168-05	nndz-WkNDOHlMbnhndz09	4513	t	\N	1	7	12.50		2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
324989	\N	Susan	Fortier	4611	4355	2025-06-24 19:48:53.831168-05	nndz-WkNDOHlMei9qQT09	4513	t	\N	1	7	12.50		2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
324990	\N	Jane	Hutson	4611	4355	2025-06-24 19:48:53.831168-05	nndz-WkNDOHlMaitoQT09	4513	t	\N	1	4	20.00		2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
324991	\N	Patty	Buckingham	4611	4355	2025-06-24 19:48:53.831168-05	nndz-WkNDOHlMei9oUT09	4513	t	\N	2	7	22.20		2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
324992	\N	Meredith	Richard	4611	4355	2025-06-24 19:48:53.831168-05	nndz-WkNDL3dicjVqQT09	4513	t	\N	1	7	12.50		2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
324993	\N	Krissy	Struckman	4611	4355	2025-06-24 19:48:53.831168-05	nndz-WkNDOHlMei9qUT09	4513	t	\N	0	0	0.00		2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
324994	\N	Katie	Baisley	4611	4355	2025-06-24 19:48:53.831168-05	nndz-WkM2eHhMZnhodz09	4513	t	\N	6	5	54.50		2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
324995	\N	Caroline	Heitmann	4611	4355	2025-06-24 19:48:53.831168-05	nndz-WkM2eHhycitqQT09	4513	t	\N	5	6	45.50		2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
324996	\N	Katie	LaVoy	4611	4355	2025-06-24 19:48:53.831168-05	nndz-WkNHN3didjhodz09	4513	t	\N	5	4	55.60		2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
324997	\N	Stacy	McCourt	4611	4355	2025-06-24 19:48:53.831168-05	nndz-WkM2d3c3djRodz09	4513	t	\N	4	5	44.40		2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
324998	\N	Kari	McNeil	4611	4355	2025-06-24 19:48:53.831168-05	nndz-WkNDOHlMYndnQT09	4513	t	\N	5	4	55.60		2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
324999	\N	Annie	Nicolau	4611	4355	2025-06-24 19:48:53.831168-05	nndz-WkM2eHhycnhoUT09	4513	t	\N	5	5	50.00		2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
325000	\N	Stephanie	Selby	4611	4355	2025-06-24 19:48:53.831168-05	nndz-WkM2eHhycnhoZz09	4513	t	\N	10	5	66.70		2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
325001	\N	Lauren	Silverman	4637	4356	2025-06-24 19:48:53.831168-05	nndz-WkM2eHg3bjloQT09	4513	t	\N	4	8	33.30	C	2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
325002	\N	Maureen	DeRose	4637	4356	2025-06-24 19:48:53.831168-05	nndz-WkNDOHlMcjZnZz09	4513	t	\N	2	2	50.00	CC	2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
325003	\N	Kelli	Abboud	4637	4356	2025-06-24 19:48:53.831168-05	nndz-WkNDOHlMcjZoZz09	4513	t	\N	4	2	66.70		2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
325004	\N	Susan	Felitto	4637	4356	2025-06-24 19:48:53.831168-05	nndz-WkNDOHlMdi9oZz09	4513	t	\N	4	2	66.70		2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
325005	\N	Marita	Janzen-Grady	4637	4356	2025-06-24 19:48:53.831168-05	nndz-WkNDK3hiZi9ndz09	4513	t	\N	2	4	33.30		2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
325006	\N	Susan	Jones	4637	4356	2025-06-24 19:48:53.831168-05	nndz-WkNDOHlMajRodz09	4513	t	\N	2	4	33.30		2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
325007	\N	Jennifer	Martay	4637	4356	2025-06-24 19:48:53.831168-05	nndz-WkNDOHlMdjhnUT09	4513	t	\N	2	5	28.60		2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
325008	\N	Jill	Mirkovic	4637	4356	2025-06-24 19:48:53.831168-05	nndz-WkNDOHlMcjZodz09	4513	t	\N	0	5	0.00		2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
325009	\N	Yvette	Stewart	4637	4356	2025-06-24 19:48:53.831168-05	nndz-WkNDOHlMcjdqUT09	4513	t	\N	3	4	42.90		2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
325010	\N	Tiffany	Thoelecke	4637	4356	2025-06-24 19:48:53.831168-05	nndz-WkNDOHlMcjdoQT09	4513	t	\N	4	4	50.00		2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
325011	\N	Sara	Walker	4637	4356	2025-06-24 19:48:53.831168-05	nndz-WkNDOHlMcjloUT09	4513	t	\N	4	4	50.00		2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
325012	\N	Cyndi	Barrett	4637	4356	2025-06-24 19:48:53.831168-05	nndz-WkNDOHlMcjdqQT09	4513	t	\N	0	0	0.00		2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
325013	\N	Andi	Bolan	4637	4356	2025-06-24 19:48:53.831168-05	nndz-WkNDOHlMcjdnQT09	4513	t	\N	0	0	0.00		2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
325014	\N	Molly	Tatham	4637	4356	2025-06-24 19:48:53.831168-05	nndz-WkNDOHlMandnUT09	4513	t	\N	0	0	0.00		2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
325015	\N	Kelly	Hondru	4637	4356	2025-06-24 19:48:53.831168-05	nndz-WkM2eHg3bjZoUT09	4513	t	\N	7	3	70.00		2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
325016	\N	Jennifer	Gallagher	4637	4357	2025-06-24 19:48:53.831168-05	nndz-WkNDOHlMcjloQT09	4513	t	\N	1	5	16.70	C	2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
325017	\N	Erin	Lamb	4637	4357	2025-06-24 19:48:53.831168-05	nndz-WkNDOHlMcjlnUT09	4513	t	\N	1	6	14.30	CC	2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
325018	\N	Dana	Anderson	4637	4357	2025-06-24 19:48:53.831168-05	nndz-WkNDOHlMcjlqQT09	4513	t	\N	1	5	16.70		2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
325019	\N	Janet	Beatty	4637	4357	2025-06-24 19:48:53.831168-05	nndz-WkNDOHlMdi9ndz09	4513	t	\N	4	3	57.10		2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
325020	\N	Carol	Carlson	4637	4357	2025-06-24 19:48:53.831168-05	nndz-WkM2eHg3bjloUT09	4513	t	\N	3	8	27.30		2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
325021	\N	Sarah	Cyphers	4637	4357	2025-06-24 19:48:53.831168-05	nndz-WkM2eHg3ajloUT09	4513	t	\N	4	3	57.10		2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
325022	\N	Andrea	Denes	4637	4357	2025-06-24 19:48:53.831168-05	nndz-WkM2eHg3bjlnQT09	4513	t	\N	3	5	37.50		2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
325023	\N	Kimberly	Gorham	4637	4357	2025-06-24 19:48:53.831168-05	nndz-WkNDOHlMcjdnUT09	4513	t	\N	3	4	42.90		2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
325024	\N	Jane	Lustig	4637	4357	2025-06-24 19:48:53.831168-05	nndz-WkNDL3diN3doQT09	4513	t	\N	5	7	41.70		2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
325025	\N	Melissa	Read	4637	4357	2025-06-24 19:48:53.831168-05	nndz-WkNDOHlMai9oZz09	4513	t	\N	3	4	42.90		2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
325026	\N	Cyndi	Barrett	4637	4357	2025-06-24 19:48:53.831168-05	nndz-WkNDOHlMcjdqQT09	4513	t	\N	0	0	0.00		2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
325027	\N	Andi	Bolan	4637	4357	2025-06-24 19:48:53.831168-05	nndz-WkNDOHlMcjdnQT09	4513	t	\N	0	0	0.00		2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
325028	\N	Molly	Tatham	4637	4357	2025-06-24 19:48:53.831168-05	nndz-WkNDOHlMandnUT09	4513	t	\N	0	0	0.00		2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
325029	\N	Gia	Diakakis	4637	4357	2025-06-24 19:48:53.831168-05	nndz-WkM2eHg3bjdqUT09	4513	t	\N	15	5	75.00		2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
325030	\N	Erika	Phenner	4637	4357	2025-06-24 19:48:53.831168-05	nndz-WkM2eHg3bjZndz09	4513	t	\N	6	2	75.00		2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
325031	\N	Jacki	Ruh	4637	4357	2025-06-24 19:48:53.831168-05	nndz-WkNDL3didnhqUT09	4513	t	\N	5	1	83.30		2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
325032	\N	Judy	Yoo	4637	4357	2025-06-24 19:48:53.831168-05	nndz-WkM2eHg3bjZqQT09	4513	t	\N	11	5	68.80		2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
325033	\N	Kristen	Fragale	4642	4355	2025-06-24 19:48:53.831168-05	nndz-WkNDL3diNy9oQT09	4513	t	\N	6	2	75.00	C	2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
325034	\N	Kim	Soifer	4642	4355	2025-06-24 19:48:53.831168-05	nndz-WkM2eHc3NzVnQT09	4513	t	\N	14	10	58.30	CC	2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
325035	\N	Karli	Bertocchi	4642	4355	2025-06-24 19:48:53.831168-05	nndz-WkNHNHlMLzZqQT09	4513	t	\N	10	3	76.90		2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
325036	\N	Patti	Charman	4642	4355	2025-06-24 19:48:53.831168-05	nndz-WkNDK3lMZjVoUT09	4513	t	\N	6	1	85.70		2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
325037	\N	Beth	Cole	4642	4355	2025-06-24 19:48:53.831168-05	nndz-WkNDOHlMNzhndz09	4513	t	\N	5	2	71.40		2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
325038	\N	Kathy	Hinkel	4642	4355	2025-06-24 19:48:53.831168-05	nndz-WkM2eHg3LzlqUT09	4513	t	\N	12	4	75.00		2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
325039	\N	Karen	Pinsof	4642	4355	2025-06-24 19:48:53.831168-05	nndz-WkNDOHlMbjVndz09	4513	t	\N	2	2	50.00		2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
325040	\N	Maribeth	Roberti	4642	4355	2025-06-24 19:48:53.831168-05	nndz-WkNDOHlMajdnQT09	4513	t	\N	4	2	66.70		2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
325041	\N	Sue	Weitzman	4642	4355	2025-06-24 19:48:53.831168-05	nndz-WkNDOHlMdjhodz09	4513	t	\N	4	2	66.70		2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
325042	\N	Jill	Zisook	4642	4355	2025-06-24 19:48:53.831168-05	nndz-WkNDOHlMNzhnZz09	4513	t	\N	2	4	33.30		2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
325043	\N	Elizabeth	Jensen	4642	4355	2025-06-24 19:48:53.831168-05	nndz-WkNHNXdyZitoQT09	4513	t	\N	6	6	50.00		2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
325044	\N	Lauren	Kane	4642	4355	2025-06-24 19:48:53.831168-05	nndz-WkM2eHhMYi9oUT09	4513	t	\N	8	4	66.70		2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
325045	\N	Liz	Krupkin	4642	4355	2025-06-24 19:48:53.831168-05	nndz-WkNHNHlMcjVoQT09	4513	t	\N	7	5	58.30		2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
325046	\N	Anne	Babick	4646	4356	2025-06-24 19:48:53.831168-05	nndz-WkM2eHdycjRoQT09	4513	t	\N	4	4	50.00	C	2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
325047	\N	Anne	Honzel	4646	4356	2025-06-24 19:48:53.831168-05	nndz-WkNDOHlMdjlqQT09	4513	t	\N	6	3	66.70	CC	2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
325048	\N	Ann	Barrett	4646	4356	2025-06-24 19:48:53.831168-05	nndz-WkNDOHlMeitqQT09	4513	t	\N	0	0	0.00		2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
325049	\N	Freddi	Brown	4646	4356	2025-06-24 19:48:53.831168-05	nndz-WkNDOHlMN3dqQT09	4513	t	\N	3	5	37.50		2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
325050	\N	Julie	Feeney	4646	4356	2025-06-24 19:48:53.831168-05	nndz-WkNDOHlMejdoUT09	4513	t	\N	3	5	37.50		2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
325051	\N	Debra	Kaden	4646	4356	2025-06-24 19:48:53.831168-05	nndz-WkNDL3diNzlodz09	4513	t	\N	8	8	50.00		2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
325052	\N	Heidi	McGarry	4646	4356	2025-06-24 19:48:53.831168-05	nndz-WkNDOHlMLzVoZz09	4513	t	\N	6	3	66.70		2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
325053	\N	Kendal	Reis	4646	4356	2025-06-24 19:48:53.831168-05	nndz-WkNDL3diLzZqQT09	4513	t	\N	4	4	50.00		2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
325054	\N	Amy	Rogers	4646	4356	2025-06-24 19:48:53.831168-05	nndz-WkNDOHlMajVnUT09	4513	t	\N	1	2	33.30		2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
325055	\N	Carolyn	Streett	4646	4356	2025-06-24 19:48:53.831168-05	nndz-WlNhNnliYnhoUT09	4513	t	\N	3	2	60.00		2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
325056	\N	Joanne	Wallace	4646	4356	2025-06-24 19:48:53.831168-05	nndz-WkM2eHdycjVoUT09	4513	t	\N	0	0	0.00		2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
325057	\N	Susan	Deloach	4646	4356	2025-06-24 19:48:53.831168-05	nndz-WkNDOHlMN3dqUT09	4513	t	\N	0	0	0.00		2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
325058	\N	Ellen	Dooley	4646	4356	2025-06-24 19:48:53.831168-05	nndz-WkM2eHliL3hnQT09	4513	t	\N	0	2	0.00		2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
325059	\N	Lisa	Jamieson	4646	4356	2025-06-24 19:48:53.831168-05	nndz-WkNDOHlMeitnQT09	4513	t	\N	2	1	66.70		2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
325060	\N	Meg	McDonnell	4646	4356	2025-06-24 19:48:53.831168-05	nndz-WkNDOHlMajhnUT09	4513	t	\N	2	0	100.00		2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
325061	\N	Liz	Paul	4646	4356	2025-06-24 19:48:53.831168-05	nndz-WkNDOHlMdndodz09	4513	t	\N	0	0	0.00		2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
325062	\N	Lowey	Sichol	4646	4356	2025-06-24 19:48:53.831168-05	nndz-WkNDOHlMajRnQT09	4513	t	\N	0	0	0.00		2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
325063	\N	Leslie	Parsons	4646	4357	2025-06-24 19:48:53.831168-05	nndz-WkNDOHlMajVqUT09	4513	t	\N	3	5	37.50	C	2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
325064	\N	Carmel	Glynn	4646	4357	2025-06-24 19:48:53.831168-05	nndz-WkNDOHlMZi9nQT09	4513	t	\N	3	6	33.30	CC	2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
325065	\N	Emily	Ciaglo	4646	4357	2025-06-24 19:48:53.831168-05	nndz-WkNHNXc3cjhoQT09	4513	t	\N	3	6	33.30		2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
325066	\N	Cari	Gold	4646	4357	2025-06-24 19:48:53.831168-05	nndz-WkNDL3diLzhodz09	4513	t	\N	7	6	53.80		2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
325067	\N	Carrie	Miller Mygatt	4646	4357	2025-06-24 19:48:53.831168-05	nndz-WkNDL3diLy9nZz09	4513	t	\N	9	5	64.30		2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
325068	\N	Catherine	Murdoch	4646	4357	2025-06-24 19:48:53.831168-05	nndz-WkNDOHlMdjRnZz09	4513	t	\N	1	6	14.30		2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
325069	\N	Claire	Perry	4646	4357	2025-06-24 19:48:53.831168-05	nndz-WkNDOHlMMytoQT09	4513	t	\N	3	5	37.50		2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
325070	\N	Diane	Powell	4646	4357	2025-06-24 19:48:53.831168-05	nndz-WkNDL3diendqUT09	4513	t	\N	0	0	0.00		2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
325071	\N	Erin	Quinn	4646	4357	2025-06-24 19:48:53.831168-05	nndz-WkNDL3dicnhqUT09	4513	t	\N	9	5	64.30		2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
325072	\N	Casey	Russell	4646	4357	2025-06-24 19:48:53.831168-05	nndz-WkNDOHlMajVqQT09	4513	t	\N	3	5	37.50		2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
325073	\N	Beth	Beeler	4646	4357	2025-06-24 19:48:53.831168-05	nndz-WkM2eHhidjZqUT09	4513	t	\N	6	8	42.90		2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
325074	\N	Michel	Mahaffey	4646	4357	2025-06-24 19:48:53.831168-05	nndz-WkNDOHlMYjlnQT09	4513	t	\N	2	6	25.00		2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
325075	\N	Kathy	Pagano	4646	4357	2025-06-24 19:48:53.831168-05	nndz-WkNDL3diN3dnZz09	4513	t	\N	2	5	28.60		2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
325076	\N	Elizabeth	Samartzis	4646	4357	2025-06-24 19:48:53.831168-05	nndz-WkNDL3diejZndz09	4513	t	\N	5	2	71.40		2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
325077	\N	Amy	Cole	4572	4358	2025-06-24 19:48:53.831168-05	nndz-WkNDOHlMdnhodz09	4513	t	\N	2	4	33.30	C	2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
325078	\N	Hillary	Heyden	4572	4358	2025-06-24 19:48:53.831168-05	nndz-WkM2eHg3ejdoUT09	4513	t	\N	7	2	77.80	CC	2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
325079	\N	Suzanne	Alexander	4572	4358	2025-06-24 19:48:53.831168-05	nndz-WkNDOHlMZjhnZz09	4513	t	\N	1	6	14.30		2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
325080	\N	Lisa	Aronson	4572	4358	2025-06-24 19:48:53.831168-05	nndz-WkNDOHlMditqQT09	4513	t	\N	0	1	0.00		2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
325081	\N	Geri	Greenberg	4572	4358	2025-06-24 19:48:53.831168-05	nndz-WkNDOHlMdnhoZz09	4513	t	\N	0	3	0.00		2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
325082	\N	Barbie	Hecktman	4572	4358	2025-06-24 19:48:53.831168-05	nndz-WkNDOHlMditqUT09	4513	t	\N	1	5	16.70		2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
325083	\N	Michelle	Kosner	4572	4358	2025-06-24 19:48:53.831168-05	nndz-WkNDL3didndqUT09	4513	t	\N	0	2	0.00		2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
325084	\N	Amy	Perlmutter	4572	4358	2025-06-24 19:48:53.831168-05	nndz-WkNDOHlMditoUT09	4513	t	\N	2	1	66.70		2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
325085	\N	Dannit	Schneider	4572	4358	2025-06-24 19:48:53.831168-05	nndz-WkM2eHg3ejRqQT09	4513	t	\N	5	3	62.50		2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
325086	\N	Lisa	Schulman	4572	4358	2025-06-24 19:48:53.831168-05	nndz-WkNDOHlMditnUT09	4513	t	\N	1	0	100.00		2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
325087	\N	Lynne	Shapiro	4572	4358	2025-06-24 19:48:53.831168-05	nndz-WkNDOHlMajRnZz09	4513	t	\N	0	6	0.00		2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
325088	\N	Jenny	Strimling	4572	4358	2025-06-24 19:48:53.831168-05	nndz-WkNDOHlMZjhnQT09	4513	t	\N	3	6	33.30		2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
325089	\N	Julie	Winicour	4572	4358	2025-06-24 19:48:53.831168-05	nndz-WkNDOHlMZjhnUT09	4513	t	\N	2	5	28.60		2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
325090	\N	Celeste	Center	4572	4358	2025-06-24 19:48:53.831168-05	nndz-WkNDK3hiZi9qQT09	4513	t	\N	0	1	0.00		2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
325091	\N	Jenny	Piermont	4572	4358	2025-06-24 19:48:53.831168-05	nndz-WkM2eHlicjZnQT09	4513	t	\N	10	1	90.90		2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
325092	\N	Whitney	Weiner	4572	4358	2025-06-24 19:48:53.831168-05	nndz-WlNlN3hiYjVoZz09	4513	t	\N	8	2	80.00		2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
325093	\N	Meredith	Gainer	4579	4358	2025-06-24 19:48:53.831168-05	nndz-WkNDL3diMzZodz09	4513	t	\N	5	2	71.40	C	2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
325094	\N	Maggie	DePalo	4579	4358	2025-06-24 19:48:53.831168-05	nndz-WkNHNXc3M3hnZz09	4513	t	\N	6	1	85.70	CC	2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
325095	\N	Katie	Bailey	4579	4358	2025-06-24 19:48:53.831168-05	nndz-WkNDOHlMLzVoUT09	4513	t	\N	0	2	0.00		2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
325096	\N	Kristen	Denicolo	4579	4358	2025-06-24 19:48:53.831168-05	nndz-WkNDL3diLytoQT09	4513	t	\N	2	4	33.30		2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
325097	\N	Margaret	Flanagan	4579	4358	2025-06-24 19:48:53.831168-05	nndz-WkNDOHlMYjZqQT09	4513	t	\N	2	3	40.00		2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
325098	\N	Karen	Kurkowski	4579	4358	2025-06-24 19:48:53.831168-05	nndz-WkNDL3diLytnZz09	4513	t	\N	1	5	16.70		2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
325099	\N	Nancy	Lagousakos	4579	4358	2025-06-24 19:48:53.831168-05	nndz-WkNDOHlMYjlodz09	4513	t	\N	4	1	80.00		2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
325100	\N	Catherine	Marrs	4579	4358	2025-06-24 19:48:53.831168-05	nndz-WkNDL3diLytoUT09	4513	t	\N	2	4	33.30		2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
325101	\N	Cathy	Omundson	4579	4358	2025-06-24 19:48:53.831168-05	nndz-WkNDOHlMN3dnZz09	4513	t	\N	3	3	50.00		2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
325102	\N	Daria	Rickett	4579	4358	2025-06-24 19:48:53.831168-05	nndz-WkNDOHlMdi9oUT09	4513	t	\N	5	1	83.30		2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
325103	\N	Sun	Such	4579	4358	2025-06-24 19:48:53.831168-05	nndz-WkNHNHdMZi9nZz09	4513	t	\N	2	6	25.00		2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
325104	\N	Jenni	Suvari	4579	4358	2025-06-24 19:48:53.831168-05	nndz-WkNDOHlMZjdnUT09	4513	t	\N	1	5	16.70		2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
325105	\N	Erin	Donohoe	4579	4358	2025-06-24 19:48:53.831168-05	nndz-WkM2eHg3cndnZz09	4513	t	\N	2	7	22.20		2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
325106	\N	Sandy	Sherwood	4579	4358	2025-06-24 19:48:53.831168-05	nndz-WkNHNXc3ajVoUT09	4513	t	\N	0	1	0.00		2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
325107	\N	Nicole	Goven	4579	4358	2025-06-24 19:48:53.831168-05	nndz-WkNHNXc3dndoZz09	4513	t	\N	7	4	63.60		2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
325108	\N	Victoria	Willer	4593	4358	2025-06-24 19:48:53.831168-05	nndz-WkNDOHlMZjVodz09	4513	t	\N	1	6	14.30	C	2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
325109	\N	Katie	Burnside	4593	4358	2025-06-24 19:48:53.831168-05	nndz-WkM2eHg3Nytodz09	4513	t	\N	1	9	10.00	CC	2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
325110	\N	Kathy	Evertsberg	4593	4358	2025-06-24 19:48:53.831168-05	nndz-WkNDOHlMYndqQT09	4513	t	\N	0	7	0.00		2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
325111	\N	Jody	Fisher	4593	4358	2025-06-24 19:48:53.831168-05	nndz-WkNDK3lMZi9qQT09	4513	t	\N	0	0	0.00		2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
325112	\N	Mary	Freeburg	4593	4358	2025-06-24 19:48:53.831168-05	nndz-WkM2eHhyejRoUT09	4513	t	\N	0	5	0.00		2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
325113	\N	Margaret	Hart	4593	4358	2025-06-24 19:48:53.831168-05	nndz-WkNDOHlMYnhndz09	4513	t	\N	0	8	0.00		2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
325114	\N	Susie	Healey	4593	4358	2025-06-24 19:48:53.831168-05	nndz-WkNDOHlMYnhqQT09	4513	t	\N	0	0	0.00		2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
325115	\N	Tessa	Kalotis	4593	4358	2025-06-24 19:48:53.831168-05	nndz-WkNHNHlMdjdndz09	4513	t	\N	0	4	0.00		2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
325116	\N	Susan	Marren	4593	4358	2025-06-24 19:48:53.831168-05	nndz-WkNDOHlMLzdnQT09	4513	t	\N	0	6	0.00		2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
325117	\N	Sarah	Martinez	4593	4358	2025-06-24 19:48:53.831168-05	nndz-WkM2eHhyL3doUT09	4513	t	\N	0	0	0.00		2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
325118	\N	Margaret	Nelson	4593	4358	2025-06-24 19:48:53.831168-05	nndz-WkNDL3dieitoQT09	4513	t	\N	0	1	0.00		2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
325119	\N	Elizabeth	Parkinson	4593	4358	2025-06-24 19:48:53.831168-05	nndz-WkNDOHlMYnhoZz09	4513	t	\N	0	1	0.00		2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
325120	\N	Jen	Parkinson	4593	4358	2025-06-24 19:48:53.831168-05	nndz-WkM2eHhyejVoZz09	4513	t	\N	0	1	0.00		2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
325121	\N	Marty	Peterson Shaw	4593	4358	2025-06-24 19:48:53.831168-05	nndz-WkNDL3dieitoUT09	4513	t	\N	0	5	0.00		2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
325122	\N	Mary	Potter	4593	4358	2025-06-24 19:48:53.831168-05	nndz-WkNHNXdyZnhoUT09	4513	t	\N	0	9	0.00		2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
325123	\N	Elizabeth	Queen	4593	4358	2025-06-24 19:48:53.831168-05	nndz-WkMreHdMcnhodz09	4513	t	\N	0	0	0.00		2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
325124	\N	Elizabeth	Moore	4593	4358	2025-06-24 19:48:53.831168-05	nndz-WkM2eHhyL3doQT09	4513	t	\N	2	1	66.70		2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
325125	\N	Amy	Gray	4593	4358	2025-06-24 19:48:53.831168-05	nndz-WkNDK3lMZjlnZz09	4513	t	\N	0	0	0.00		2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
325126	\N	Jackie	Magner	4593	4358	2025-06-24 19:48:53.831168-05	nndz-WkNDOHlMLzdqQT09	4513	t	\N	0	3	0.00		2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
325127	\N	Libby	Graham	4593	4358	2025-06-24 19:48:53.831168-05	nndz-WkMrK3lMNzRoUT09	4513	t	\N	3	7	30.00		2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
325128	\N	Jessica	Montgomery	4593	4358	2025-06-24 19:48:53.831168-05	nndz-WkM2eHhyejRnZz09	4513	t	\N	1	6	14.30		2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
325129	\N	Adrienne	Weisenberger	4593	4358	2025-06-24 19:48:53.831168-05	nndz-WkNDL3diL3hoZz09	4513	t	\N	1	2	33.30		2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
325130	\N	Janie	Priola	4600	4358	2025-06-24 19:48:53.831168-05	nndz-WkMrK3g3NzVodz09	4513	t	\N	8	1	88.90	C	2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
325131	\N	Tiffany	Alexander	4600	4358	2025-06-24 19:48:53.831168-05	nndz-WkM2eHhyendnZz09	4513	t	\N	3	4	42.90		2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
325132	\N	Amy	Cicero	4600	4358	2025-06-24 19:48:53.831168-05	nndz-WkM2eHhyMzdodz09	4513	t	\N	6	8	42.90		2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
325133	\N	Doni	Farr	4600	4358	2025-06-24 19:48:53.831168-05	nndz-WkM2eHhyMzRnQT09	4513	t	\N	5	5	50.00		2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
325134	\N	Kate	Fencl	4600	4358	2025-06-24 19:48:53.831168-05	nndz-WkM2eHg3ejdnZz09	4513	t	\N	10	5	66.70		2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
325135	\N	Kim	Frick	4600	4358	2025-06-24 19:48:53.831168-05	nndz-WkNHNXdMdjdqQT09	4513	t	\N	5	3	62.50		2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
325136	\N	Linda	Hall	4600	4358	2025-06-24 19:48:53.831168-05	nndz-WkM2eHhyMzdnQT09	4513	t	\N	6	8	42.90		2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
325137	\N	Kristin	Oneil	4600	4358	2025-06-24 19:48:53.831168-05	nndz-WkMrNnc3ajloZz09	4513	t	\N	1	2	33.30		2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
325138	\N	Kelly	Brincat	4600	4358	2025-06-24 19:48:53.831168-05	nndz-WkNDOHlMZjdoZz09	4513	t	\N	4	4	50.00		2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
325139	\N	Jenna	Zilka	4600	4358	2025-06-24 19:48:53.831168-05	nndz-WkM2eHhyMzdoQT09	4513	t	\N	3	4	42.90		2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
325140	\N	Suzanne	Bentley	4600	4358	2025-06-24 19:48:53.831168-05	nndz-WkNDOHlML3hoQT09	4513	t	\N	0	0	0.00		2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
325141	\N	Blair	Church	4600	4358	2025-06-24 19:48:53.831168-05	nndz-WkM2eHhyMzZnUT09	4513	t	\N	6	7	46.20		2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
325142	\N	Lorraine	Freedman	4600	4358	2025-06-24 19:48:53.831168-05	nndz-WkNDOHlMLytodz09	4513	t	\N	3	1	75.00		2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
325143	\N	Caryllon	Huggins	4600	4358	2025-06-24 19:48:53.831168-05	nndz-WkNDOHlML3hqUT09	4513	t	\N	0	0	0.00		2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
325144	\N	Natalie	Reinkemeyer	4600	4358	2025-06-24 19:48:53.831168-05	nndz-WkNDOHlMLy9qUT09	4513	t	\N	5	2	71.40		2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
325145	\N	Kim	Ratkin	4608	4358	2025-06-24 19:48:53.831168-05	nndz-WkNDOHlMbjZodz09	4513	t	\N	6	5	54.50	C	2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
325146	\N	Robin	Thompson	4608	4358	2025-06-24 19:48:53.831168-05	nndz-WkM2eHg3NzRnQT09	4513	t	\N	5	7	41.70	CC	2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
325147	\N	Mary	Anderson	4608	4358	2025-06-24 19:48:53.831168-05	nndz-WkNDOHlMYjRqQT09	4513	t	\N	5	6	45.50		2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
325148	\N	Liesel	Brown	4608	4358	2025-06-24 19:48:53.831168-05	nndz-WkNDOHlMZi9ndz09	4513	t	\N	5	3	62.50		2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
325149	\N	Nikki	Circolone	4608	4358	2025-06-24 19:48:53.831168-05	nndz-WkNDOHlMYjRnQT09	4513	t	\N	4	2	66.70		2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
325150	\N	Lanie	Coldwell	4608	4358	2025-06-24 19:48:53.831168-05	nndz-WkNDL3diditndz09	4513	t	\N	2	5	28.60		2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
325151	\N	Lauri	Harris	4608	4358	2025-06-24 19:48:53.831168-05	nndz-WkNDL3diejVoQT09	4513	t	\N	6	2	75.00		2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
325152	\N	Robin	Hungler	4608	4358	2025-06-24 19:48:53.831168-05	nndz-WkNDOHlMNy9ndz09	4513	t	\N	4	7	36.40		2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
325153	\N	Carrie	Moysey	4608	4358	2025-06-24 19:48:53.831168-05	nndz-WkNHNHlMLzVqQT09	4513	t	\N	6	3	66.70		2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
325154	\N	Kristin	Alcala	4608	4358	2025-06-24 19:48:53.831168-05	nndz-WkNHNXdMcndodz09	4513	t	\N	13	4	76.50		2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
325155	\N	Katherine	Byrnes	4608	4358	2025-06-24 19:48:53.831168-05	nndz-WkNDL3diejVoUT09	4513	t	\N	0	0	0.00		2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
325156	\N	Maddie	Knowland	4608	4358	2025-06-24 19:48:53.831168-05	nndz-WkM2eHg3ejdqQT09	4513	t	\N	6	3	66.70		2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
325157	\N	Domenica	Waslin	4608	4358	2025-06-24 19:48:53.831168-05	nndz-WkM2eHg3N3hnQT09	4513	t	\N	6	1	85.70		2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
325158	\N	Laurie	Gillman	4610	4358	2025-06-24 19:48:53.831168-05	nndz-WkNDOHlMMy9odz09	4513	t	\N	9	2	81.80	C	2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
325159	\N	Wendy	Beard	4610	4358	2025-06-24 19:48:53.831168-05	nndz-WkNDOHlMei9nQT09	4513	t	\N	5	1	83.30		2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
325160	\N	Hilary	Bruce	4610	4358	2025-06-24 19:48:53.831168-05	nndz-WkNDOHlMMy9oZz09	4513	t	\N	12	4	75.00		2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
325161	\N	Agnes	Hong	4610	4358	2025-06-24 19:48:53.831168-05	nndz-WkM2eHhMZjhndz09	4513	t	\N	6	1	85.70		2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
325162	\N	Liz	Joubert	4610	4358	2025-06-24 19:48:53.831168-05	nndz-WkM2eHhycjlndz09	4513	t	\N	6	2	75.00		2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
325163	\N	colette	kelsey	4610	4358	2025-06-24 19:48:53.831168-05	nndz-WkNDOHlMMy9ndz09	4513	t	\N	0	0	0.00		2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
325164	\N	Tina	Lagges	4610	4358	2025-06-24 19:48:53.831168-05	nndz-WkNHN3dyejRoZz09	4513	t	\N	0	0	0.00		2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
325165	\N	Corinne	Pinsof-Kaplan	4610	4358	2025-06-24 19:48:53.831168-05	nndz-WkNDOHlMai9oQT09	4513	t	\N	4	3	57.10		2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
325166	\N	Trisha	Pray	4610	4358	2025-06-24 19:48:53.831168-05	nndz-WkNDOHlMN3hndz09	4513	t	\N	7	4	63.60		2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
325167	\N	Aimee	Sullivan	4610	4358	2025-06-24 19:48:53.831168-05	nndz-WkNDOHlMLzhqQT09	4513	t	\N	5	1	83.30		2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
325168	\N	Erin	Alvarez	4610	4358	2025-06-24 19:48:53.831168-05	nndz-WkNHNXdMbitnUT09	4513	t	\N	5	3	62.50		2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
325169	\N	LorRhonda	Miller	4610	4358	2025-06-24 19:48:53.831168-05	nndz-WkNDOHlMMy9nZz09	4513	t	\N	11	2	84.60		2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
325170	\N	Laurie	Redman	4610	4358	2025-06-24 19:48:53.831168-05	nndz-WkNDOHlMMytoUT09	4513	t	\N	3	7	30.00		2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
325171	\N	Melissa	Schopin	4610	4358	2025-06-24 19:48:53.831168-05	nndz-WlNlN3g3cjRoZz09	4513	t	\N	6	4	60.00		2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
325172	\N	Mary	Beth Donner	4639	4358	2025-06-24 19:48:53.831168-05	nndz-WkM2eHhyYjlndz09	4513	t	\N	6	5	54.50	C	2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
325173	\N	Alixe	Small	4639	4358	2025-06-24 19:48:53.831168-05	nndz-WkNDOHlMcndndz09	4513	t	\N	2	5	28.60	CC	2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
325174	\N	Patty	Boos	4639	4358	2025-06-24 19:48:53.831168-05	nndz-WkNDL3diN3dnUT09	4513	t	\N	3	3	50.00		2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
325175	\N	Staci	Emerson	4639	4358	2025-06-24 19:48:53.831168-05	nndz-WkNDL3diejZoZz09	4513	t	\N	5	3	62.50		2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
325176	\N	Jennifer	Gnospelius	4639	4358	2025-06-24 19:48:53.831168-05	nndz-WkNDOHlMcndodz09	4513	t	\N	0	0	0.00		2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
325177	\N	Kara	Haravon	4639	4358	2025-06-24 19:48:53.831168-05	nndz-WkNDL3diLzVodz09	4513	t	\N	3	4	42.90		2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
325178	\N	Dana	Palmer	4639	4358	2025-06-24 19:48:53.831168-05	nndz-WkNDOHlMZnhoQT09	4513	t	\N	4	4	50.00		2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
325179	\N	Tracy	Reeder	4639	4358	2025-06-24 19:48:53.831168-05	nndz-WkNDOHlMZnhodz09	4513	t	\N	4	4	50.00		2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
325180	\N	Beth	Schmidt	4639	4358	2025-06-24 19:48:53.831168-05	nndz-WkNDOHlMdjVoZz09	4513	t	\N	2	4	33.30		2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
325181	\N	Stef	Turner	4639	4358	2025-06-24 19:48:53.831168-05	nndz-WkM2eHhyYi9oUT09	4513	t	\N	4	3	57.10		2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
325182	\N	Shay	Cwick	4639	4358	2025-06-24 19:48:53.831168-05	nndz-WkM2eHhyYnhnZz09	4513	t	\N	8	4	66.70		2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
325183	\N	Rachel	Bowlin	4639	4358	2025-06-24 19:48:53.831168-05	nndz-WkM2eHhyYi9nUT09	4513	t	\N	8	3	72.70		2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
325184	\N	Pam	Hartigan	4639	4358	2025-06-24 19:48:53.831168-05	nndz-WkNDOHlMcnhqQT09	4513	t	\N	4	3	57.10		2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
325185	\N	Cynthia	Reeder	4639	4358	2025-06-24 19:48:53.831168-05	nndz-WkM2eHg3LzlnUT09	4513	t	\N	4	6	40.00		2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
325186	\N	Nora	Waryas	4639	4358	2025-06-24 19:48:53.831168-05	nndz-WkM2eHhyYjZoQT09	4513	t	\N	8	5	61.50		2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
325187	\N	Lindsay	Shull	4640	4358	2025-06-24 19:48:53.831168-05	nndz-WkM2eHg3NzZoZz09	4513	t	\N	3	4	42.90	C	2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
325188	\N	Anna	Marie Close	4640	4358	2025-06-24 19:48:53.831168-05	nndz-WkNDL3diejloUT09	4513	t	\N	6	6	50.00	CC	2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
325189	\N	Katarina	Keneally	4640	4358	2025-06-24 19:48:53.831168-05	nndz-WkNDL3diMytqQT09	4513	t	\N	8	4	66.70		2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
325190	\N	Katie	Minahan	4640	4358	2025-06-24 19:48:53.831168-05	nndz-WkNHNXc3ci9oUT09	4513	t	\N	4	1	80.00		2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
325191	\N	Tina	Newell	4640	4358	2025-06-24 19:48:53.831168-05	nndz-WkNDOHlMdjZoZz09	4513	t	\N	8	4	66.70		2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
325192	\N	Pamela	Norris	4640	4358	2025-06-24 19:48:53.831168-05	nndz-WkNDL3dicitoZz09	4513	t	\N	2	8	20.00		2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
325193	\N	Megan	Panje-Wilson	4640	4358	2025-06-24 19:48:53.831168-05	nndz-WkNDL3diZnhnQT09	4513	t	\N	6	5	54.50		2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
325194	\N	Megan	Roberts	4640	4358	2025-06-24 19:48:53.831168-05	nndz-WkNDL3diZnhodz09	4513	t	\N	6	2	75.00		2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
325195	\N	Jeannie	Schafer	4640	4358	2025-06-24 19:48:53.831168-05	nndz-WkNDL3dMendnZz09	4513	t	\N	0	0	0.00		2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
325196	\N	Lea	Halvadia	4640	4358	2025-06-24 19:48:53.831168-05	nndz-WkNDL3dicitnZz09	4513	t	\N	6	2	75.00		2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
325197	\N	Nicole	Doherty	4640	4358	2025-06-24 19:48:53.831168-05	nndz-WkMreHdicjhoQT09	4513	t	\N	12	4	75.00		2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
325198	\N	Adrienne	Eynon	4640	4358	2025-06-24 19:48:53.831168-05	nndz-WkM2eHhyZndodz09	4513	t	\N	13	4	76.50		2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
325199	\N	Lisa	Farrell	4640	4358	2025-06-24 19:48:53.831168-05	nndz-WkNDL3dicndoUT09	4513	t	\N	6	4	60.00		2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
325200	\N	Jenner	Schlafly	4640	4358	2025-06-24 19:48:53.831168-05	nndz-WkM2eHhyZi9oUT09	4513	t	\N	9	3	75.00		2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
325201	\N	Cathleen	Lazor	4646	4358	2025-06-24 19:48:53.831168-05	nndz-WkM2eHdycjVqQT09	4513	t	\N	5	7	41.70	C	2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
325202	\N	Beth	Beeler	4646	4358	2025-06-24 19:48:53.831168-05	nndz-WkM2eHhidjZqUT09	4513	t	\N	6	8	42.90	CC	2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
325203	\N	Jules	Ainsworth	4646	4358	2025-06-24 19:48:53.831168-05	nndz-WkM2eHdycjRoUT09	4513	t	\N	5	6	45.50		2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
325204	\N	Enza	Fragassi	4646	4358	2025-06-24 19:48:53.831168-05	nndz-WkNDL3dMenhqUT09	4513	t	\N	6	0	100.00		2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
325205	\N	Nicole	Jones	4646	4358	2025-06-24 19:48:53.831168-05	nndz-WkNDOHlMZitoUT09	4513	t	\N	8	7	53.30		2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
325206	\N	Kristen	Lutz	4646	4358	2025-06-24 19:48:53.831168-05	nndz-WkM2eHhidjZqQT09	4513	t	\N	6	6	50.00		2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
325207	\N	Jill	Olson	4646	4358	2025-06-24 19:48:53.831168-05	nndz-WkNDOHlMYjlqUT09	4513	t	\N	2	2	50.00		2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
325208	\N	Susan	Pearsall	4646	4358	2025-06-24 19:48:53.831168-05	nndz-WkNHN3dyajVnZz09	4513	t	\N	2	3	40.00		2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
325209	\N	Elizabeth	Samartzis	4646	4358	2025-06-24 19:48:53.831168-05	nndz-WkNDL3diejZndz09	4513	t	\N	5	2	71.40		2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
325210	\N	Bari	Wood	4646	4358	2025-06-24 19:48:53.831168-05	nndz-WkNDL3diLzhoQT09	4513	t	\N	4	2	66.70		2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
325211	\N	Ellen	Castellini	4646	4358	2025-06-24 19:48:53.831168-05	nndz-WkMrN3g3ajRqQT09	4513	t	\N	8	7	53.30		2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
325212	\N	Jen	Trzebiatowski	4646	4358	2025-06-24 19:48:53.831168-05	nndz-WkMrK3dMMy9oZz09	4513	t	\N	8	10	44.40		2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
325213	\N	Veronica	Denicolo	4649	4358	2025-06-24 19:48:53.831168-05	nndz-WkM2eHliejVnQT09	4513	t	\N	7	4	63.60	C	2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
325214	\N	Courtney	Magliochetti	4649	4358	2025-06-24 19:48:53.831168-05	nndz-WkM2eHliejVqUT09	4513	t	\N	8	1	88.90	CC	2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
325215	\N	Erin	Henkel	4649	4358	2025-06-24 19:48:53.831168-05	nndz-WkM2eHhMZndqQT09	4513	t	\N	2	4	33.30		2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
325216	\N	Michelle	Taubensee	4649	4358	2025-06-24 19:48:53.831168-05	nndz-WkM2eHliejVqQT09	4513	t	\N	5	2	71.40		2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
325217	\N	Melissa	Thoman	4649	4358	2025-06-24 19:48:53.831168-05	nndz-WkM2eHliejRoUT09	4513	t	\N	2	4	33.30		2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
325218	\N	Kasey	Wood	4649	4358	2025-06-24 19:48:53.831168-05	nndz-WkM2eHliejRoQT09	4513	t	\N	6	4	60.00		2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
325219	\N	Mary	Bauder	4649	4358	2025-06-24 19:48:53.831168-05	nndz-WkM2eHhMZndqUT09	4513	t	\N	4	4	50.00		2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
325220	\N	Hollis	Blume	4649	4358	2025-06-24 19:48:53.831168-05	nndz-WkM2eHliejVoZz09	4513	t	\N	2	5	28.60		2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
325221	\N	Krista	Hugill	4649	4358	2025-06-24 19:48:53.831168-05	nndz-WkM2eHhyMzRnZz09	4513	t	\N	7	5	58.30		2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
325222	\N	Shannon	Shader	4649	4358	2025-06-24 19:48:53.831168-05	nndz-WkNDL3didjhqQT09	4513	t	\N	7	2	77.80		2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
325223	\N	Augusta	Williams	4649	4358	2025-06-24 19:48:53.831168-05	nndz-WkMrK3hMNzRoQT09	4513	t	\N	5	4	55.60		2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
325224	\N	Jaime	Gatenio	4571	4359	2025-06-24 19:48:53.831168-05	nndz-WkNHNXhiNzZndz09	4513	t	\N	2	4	33.30	C	2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
325225	\N	Anne	LoGrande	4571	4359	2025-06-24 19:48:53.831168-05	nndz-WkNDOHlMYjdnZz09	4513	t	\N	4	2	66.70	CC	2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
325226	\N	Rhonda	Abramson	4571	4359	2025-06-24 19:48:53.831168-05	nndz-WkNDL3diejhnZz09	4513	t	\N	3	5	37.50		2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
325227	\N	Stefanie	Hest	4571	4359	2025-06-24 19:48:53.831168-05	nndz-WkNHNXdyejhoUT09	4513	t	\N	3	5	37.50		2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
325228	\N	Amanda	Hirsh	4571	4359	2025-06-24 19:48:53.831168-05	nndz-WkM2eHg3cndnUT09	4513	t	\N	2	6	25.00		2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
325229	\N	Sara	Kaskel	4571	4359	2025-06-24 19:48:53.831168-05	nndz-WkNDOHlMM3hoZz09	4513	t	\N	3	6	33.30		2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
325230	\N	Melanie	Nadell	4571	4359	2025-06-24 19:48:53.831168-05	nndz-WkMrN3hMejhndz09	4513	t	\N	0	0	0.00		2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
325231	\N	Jennifer	Quinn	4571	4359	2025-06-24 19:48:53.831168-05	nndz-WkNDOHlMajRoZz09	4513	t	\N	5	1	83.30		2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
325232	\N	Agueda	Semrad	4571	4359	2025-06-24 19:48:53.831168-05	nndz-WkNDOHlMYjZnUT09	4513	t	\N	0	1	0.00		2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
325233	\N	Randi	Zeidel	4571	4359	2025-06-24 19:48:53.831168-05	nndz-WkNHNXdyejdnQT09	4513	t	\N	3	5	37.50		2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
325234	\N	Eve	Agin	4571	4359	2025-06-24 19:48:53.831168-05	nndz-WkNDOHlMNytndz09	4513	t	\N	0	0	0.00		2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
325235	\N	Jennifer	Engelman	4571	4359	2025-06-24 19:48:53.831168-05	nndz-WkNDL3diMzZnUT09	4513	t	\N	6	5	54.50		2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
325236	\N	Roberta	Goodman	4571	4359	2025-06-24 19:48:53.831168-05	nndz-WkNDOHlMYjRqUT09	4513	t	\N	1	2	33.30		2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
325237	\N	Jody	Rotblatt	4571	4359	2025-06-24 19:48:53.831168-05	nndz-WkM2eHhMZitoQT09	4513	t	\N	0	1	0.00		2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
325238	\N	Karen	Lothan	4571	4359	2025-06-24 19:48:53.831168-05	nndz-WkNDL3diejdodz09	4513	t	\N	3	6	33.30		2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
325239	\N	Jennifer	Markman	4571	4359	2025-06-24 19:48:53.831168-05	nndz-WkM2eHg3cndnQT09	4513	t	\N	7	2	77.80		2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
325240	\N	Melissa	Rubenstein	4571	4359	2025-06-24 19:48:53.831168-05	nndz-WkNDL3diMzdndz09	4513	t	\N	2	6	25.00		2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
325241	\N	Dara	Weil	4571	4359	2025-06-24 19:48:53.831168-05	nndz-WkNDL3diMzZqUT09	4513	t	\N	3	5	37.50		2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
325242	\N	Vanessa	Shropshire	4579	4359	2025-06-24 19:48:53.831168-05	nndz-WkNHNHlMcjloUT09	4513	t	\N	6	3	66.70	C	2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
325243	\N	Lee	Clifford	4579	4359	2025-06-24 19:48:53.831168-05	nndz-WkNHNHlMcjlodz09	4513	t	\N	7	4	63.60	CC	2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
325244	\N	Holly	Brady	4579	4359	2025-06-24 19:48:53.831168-05	nndz-WkNDOHlMYjloZz09	4513	t	\N	0	0	0.00		2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
325245	\N	Liz	Brown	4579	4359	2025-06-24 19:48:53.831168-05	nndz-WkM2eHhyNzlnUT09	4513	t	\N	0	0	0.00		2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
325246	\N	Ana	Couri	4579	4359	2025-06-24 19:48:53.831168-05	nndz-WkNDOHlMandndz09	4513	t	\N	3	4	42.90		2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
325247	\N	Rebecca	Finkelstein	4579	4359	2025-06-24 19:48:53.831168-05	nndz-WkNDL3diLytoZz09	4513	t	\N	4	3	57.10		2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
325248	\N	Susan	Ford	4579	4359	2025-06-24 19:48:53.831168-05	nndz-WkNDOHlMYjZqUT09	4513	t	\N	3	2	60.00		2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
325249	\N	Beven	Hanna	4579	4359	2025-06-24 19:48:53.831168-05	nndz-WkM2eHg3LzRnQT09	4513	t	\N	7	4	63.60		2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
325250	\N	Kelly	Lawrence	4579	4359	2025-06-24 19:48:53.831168-05	nndz-WkNDL3didjVqUT09	4513	t	\N	0	2	0.00		2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
325251	\N	Jacqueline	Souroujon-henderson	4579	4359	2025-06-24 19:48:53.831168-05	nndz-WkM2eHhyNzlndz09	4513	t	\N	4	4	50.00		2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
325252	\N	Stacy	Salgado	4579	4359	2025-06-24 19:48:53.831168-05	nndz-WkMrK3c3LzRoZz09	4513	t	\N	3	6	33.30		2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
325253	\N	Suzanne	Demirjian	4579	4359	2025-06-24 19:48:53.831168-05	nndz-WkNDeHdiNzZnUT09	4513	t	\N	0	0	0.00		2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
325254	\N	Emily	Flaherty	4579	4359	2025-06-24 19:48:53.831168-05	nndz-WkNHNHlMNzdndz09	4513	t	\N	0	0	0.00		2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
325255	\N	Erin	Donohoe	4579	4359	2025-06-24 19:48:53.831168-05	nndz-WkM2eHg3cndnZz09	4513	t	\N	2	7	22.20		2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
325256	\N	Laura	Durkin	4579	4359	2025-06-24 19:48:53.831168-05	nndz-WkNDOHlMZjdnQT09	4513	t	\N	4	1	80.00		2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
325257	\N	Nicole	Goven	4579	4359	2025-06-24 19:48:53.831168-05	nndz-WkNHNXc3dndoZz09	4513	t	\N	7	4	63.60		2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
325258	\N	Kylie	Hughes	4579	4359	2025-06-24 19:48:53.831168-05	nndz-WkM2eHg3cndqUT09	4513	t	\N	5	2	71.40		2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
325259	\N	Lexi	Marietti	4579	4359	2025-06-24 19:48:53.831168-05	nndz-WkM2eHhyNytnZz09	4513	t	\N	7	2	77.80		2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
325260	\N	Jamie	Mauceri	4579	4359	2025-06-24 19:48:53.831168-05	nndz-WkM2eHhyNzlqUT09	4513	t	\N	7	2	77.80		2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
325261	\N	Adrienne	Regis	4579	4359	2025-06-24 19:48:53.831168-05	nndz-WkM2eHg3cndqQT09	4513	t	\N	5	3	62.50		2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
325262	\N	Lydia	Barrett	4580	4359	2025-06-24 19:48:53.831168-05	nndz-WkM2eHliLzZodz09	4513	t	\N	4	5	44.40	C	2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
325263	\N	Elizabeth	Daliere	4580	4359	2025-06-24 19:48:53.831168-05	nndz-WkM2eHg3LzRqUT09	4513	t	\N	3	4	42.90		2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
325264	\N	Catherine	Gildersleeve	4580	4359	2025-06-24 19:48:53.831168-05	nndz-WkNDOHlMajRqQT09	4513	t	\N	0	0	0.00		2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
325265	\N	Carrie	Granat	4580	4359	2025-06-24 19:48:53.831168-05	nndz-WkM2eHg3LzdnUT09	4513	t	\N	1	1	50.00		2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
325266	\N	Kristin	Lambropoulos	4580	4359	2025-06-24 19:48:53.831168-05	nndz-WkM2eHhyLzdoUT09	4513	t	\N	4	4	50.00		2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
325267	\N	Lisa	McGavock	4580	4359	2025-06-24 19:48:53.831168-05	nndz-WkNDL3diei9nUT09	4513	t	\N	4	4	50.00		2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
325268	\N	Judi	Olenick	4580	4359	2025-06-24 19:48:53.831168-05	nndz-WkNDOHlMYi9odz09	4513	t	\N	2	4	33.30		2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
325269	\N	Jenn	Pattie	4580	4359	2025-06-24 19:48:53.831168-05	nndz-WkNDOHlMYjhnQT09	4513	t	\N	0	6	0.00		2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
325270	\N	Denise	Rudolph	4580	4359	2025-06-24 19:48:53.831168-05	nndz-WkNDOHlMYjhqQT09	4513	t	\N	2	5	28.60		2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
325271	\N	Lisa	Weis	4580	4359	2025-06-24 19:48:53.831168-05	nndz-WkNDOHlMYjhnUT09	4513	t	\N	4	5	44.40		2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
325272	\N	Niki	VanVuren	4580	4359	2025-06-24 19:48:53.831168-05	nndz-WkNDL3diMzRqUT09	4513	t	\N	5	4	55.60		2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
325273	\N	Mary	Jane Dee	4580	4359	2025-06-24 19:48:53.831168-05	nndz-WkNDOHlMcnhnZz09	4513	t	\N	0	0	0.00		2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
325274	\N	Billie	Diamond	4580	4359	2025-06-24 19:48:53.831168-05	nndz-WkM2eHhyLzdnZz09	4513	t	\N	9	7	56.20		2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
325275	\N	Ann	Franzese-Bourne	4580	4359	2025-06-24 19:48:53.831168-05	nndz-WlNlOXhyLzloZz09	4513	t	\N	0	0	0.00		2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
325276	\N	Kelly	Huguenard	4580	4359	2025-06-24 19:48:53.831168-05	nndz-WkNDOHlMcitnUT09	4513	t	\N	0	0	0.00		2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
325277	\N	Cyndi	Millspaugh	4580	4359	2025-06-24 19:48:53.831168-05	nndz-WkNHNXdydjlnQT09	4513	t	\N	0	0	0.00		2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
325278	\N	Patti	Poth	4580	4359	2025-06-24 19:48:53.831168-05	nndz-WkNDL3hiZjRqQT09	4513	t	\N	0	0	0.00		2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
325279	\N	Carla	Seidel	4580	4359	2025-06-24 19:48:53.831168-05	nndz-WkMrK3dyejdqUT09	4513	t	\N	0	0	0.00		2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
325280	\N	Gina	Stec	4580	4359	2025-06-24 19:48:53.831168-05	nndz-WkNDOHlMcnhndz09	4513	t	\N	0	0	0.00		2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
325281	\N	Liz	Williams	4580	4359	2025-06-24 19:48:53.831168-05	nndz-WkNDOHlMajdodz09	4513	t	\N	0	0	0.00		2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
325282	\N	Lisa	Clagg	4580	4359	2025-06-24 19:48:53.831168-05	nndz-WkM2eHhyLzRqQT09	4513	t	\N	10	3	76.90		2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
325283	\N	Anne	Hill	4599	4359	2025-06-24 19:48:53.831168-05	nndz-WkNDOHlMZjRqQT09	4513	t	\N	1	4	20.00	C	2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
325284	\N	Megan	Michael	4599	4359	2025-06-24 19:48:53.831168-05	nndz-WkNDL3diM3dndz09	4513	t	\N	4	5	44.40	CC	2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
325285	\N	Leslie	Bertholdt	4599	4359	2025-06-24 19:48:53.831168-05	nndz-WkNDOHlMLy9nUT09	4513	t	\N	2	3	40.00		2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
325286	\N	Marcy	Kerr	4599	4359	2025-06-24 19:48:53.831168-05	nndz-WkNDOHlML3hqQT09	4513	t	\N	0	1	0.00		2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
325287	\N	Becky	Koenigsknecht	4599	4359	2025-06-24 19:48:53.831168-05	nndz-WkNDL3diNzRoUT09	4513	t	\N	1	4	20.00		2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
325288	\N	Stephanie	Larson	4599	4359	2025-06-24 19:48:53.831168-05	nndz-WkNHNXdiYjlnZz09	4513	t	\N	0	0	0.00		2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
325289	\N	Rachel	McMahon	4599	4359	2025-06-24 19:48:53.831168-05	nndz-WkMrN3hMMzVodz09	4513	t	\N	3	4	42.90		2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
325290	\N	Amy	Moorman	4599	4359	2025-06-24 19:48:53.831168-05	nndz-WkNDOHlMLy9oQT09	4513	t	\N	1	4	20.00		2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
325291	\N	Martha	Pedersen	4599	4359	2025-06-24 19:48:53.831168-05	nndz-WkNDOHlMLzhndz09	4513	t	\N	2	4	33.30		2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
325292	\N	Susie	Selbst	4599	4359	2025-06-24 19:48:53.831168-05	nndz-WkM2eHhybjdoQT09	4513	t	\N	5	3	62.50		2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
325293	\N	Diane	Svanson	4599	4359	2025-06-24 19:48:53.831168-05	nndz-WkNDL3diejdqQT09	4513	t	\N	1	6	14.30		2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
325294	\N	Elizabeth	White	4599	4359	2025-06-24 19:48:53.831168-05	nndz-WkM2eHg3LzZoUT09	4513	t	\N	3	5	37.50		2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
325295	\N	Julie	Wickman	4599	4359	2025-06-24 19:48:53.831168-05	nndz-WkNDOHlMLzhnZz09	4513	t	\N	2	3	40.00		2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
325296	\N	Amy	McKernan	4599	4359	2025-06-24 19:48:53.831168-05	nndz-WkM2eHhMZjhodz09	4513	t	\N	1	1	50.00		2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
325297	\N	Renee	Edwards	4599	4359	2025-06-24 19:48:53.831168-05	nndz-WkNDOHlMLzhoZz09	4513	t	\N	0	0	0.00		2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
325298	\N	Anna	Dau	4599	4359	2025-06-24 19:48:53.831168-05	nndz-WkM2eHhyeitnZz09	4513	t	\N	6	2	75.00		2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
325299	\N	Domenica	Waslin	4608	4359	2025-06-24 19:48:53.831168-05	nndz-WkM2eHg3N3hnQT09	4513	t	\N	6	1	85.70	C	2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
325300	\N	Jennifer	Bullock	4608	4359	2025-06-24 19:48:53.831168-05	nndz-WkNDL3dicndndz09	4513	t	\N	8	1	88.90	CC	2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
325301	\N	Sara	Brahm	4608	4359	2025-06-24 19:48:53.831168-05	nndz-WkNDL3diMytoZz09	4513	t	\N	5	3	62.50		2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
325302	\N	Kristin	de Castro	4608	4359	2025-06-24 19:48:53.831168-05	nndz-WkNDL3diajVqUT09	4513	t	\N	5	3	62.50		2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
325303	\N	Aimee	Eichelberger	4608	4359	2025-06-24 19:48:53.831168-05	nndz-WkNDL3diM3hnQT09	4513	t	\N	5	3	62.50		2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
325304	\N	Allyson	Paflas	4608	4359	2025-06-24 19:48:53.831168-05	nndz-WkM2eHhMajlodz09	4513	t	\N	6	2	75.00		2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
325305	\N	Erin	Schael	4608	4359	2025-06-24 19:48:53.831168-05	nndz-WkNDOHlMZjhodz09	4513	t	\N	7	1	87.50		2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
325306	\N	Allison	Singer	4608	4359	2025-06-24 19:48:53.831168-05	nndz-WkNHNXdMcndqUT09	4513	t	\N	4	2	66.70		2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
325307	\N	Nicole	Snyder	4608	4359	2025-06-24 19:48:53.831168-05	nndz-WkNHNXdMcndqQT09	4513	t	\N	6	2	75.00		2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
325308	\N	Kristin	Alcala	4608	4359	2025-06-24 19:48:53.831168-05	nndz-WkNHNXdMcndodz09	4513	t	\N	13	4	76.50		2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
325309	\N	Simone	O'Rear	4608	4359	2025-06-24 19:48:53.831168-05	nndz-WkM2eHg3ejZoUT09	4513	t	\N	6	2	75.00		2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
325310	\N	Amy	Peters - MSC	4608	4359	2025-06-24 19:48:53.831168-05	nndz-WkM2eHhycjRodz09	4513	t	\N	14	4	77.80		2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
325311	\N	Jenna	Barnett	4612	4359	2025-06-24 19:48:53.831168-05	nndz-WkNDOHlMZnhnZz09	4513	t	\N	3	5	37.50	C	2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
325312	\N	Stacy	Auslander	4612	4359	2025-06-24 19:48:53.831168-05	nndz-WkM2eHg3YjVndz09	4513	t	\N	7	3	70.00	CC	2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
325313	\N	Susan	Abrams	4612	4359	2025-06-24 19:48:53.831168-05	nndz-WkM2d3diN3hnUT09	4513	t	\N	2	4	33.30		2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
325314	\N	Peggy	Blum	4612	4359	2025-06-24 19:48:53.831168-05	nndz-WkMrNnc3ajRnUT09	4513	t	\N	0	0	0.00		2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
325315	\N	Rana	Chandler	4612	4359	2025-06-24 19:48:53.831168-05	nndz-WkMrNnc3ajRoZz09	4513	t	\N	6	0	100.00		2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
325316	\N	Bonnie	Flanzer	4612	4359	2025-06-24 19:48:53.831168-05	nndz-WkNDOHlMai9qUT09	4513	t	\N	0	0	0.00		2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
325317	\N	Susie	Glikin	4612	4359	2025-06-24 19:48:53.831168-05	nndz-WkNDOHlMLzlnZz09	4513	t	\N	0	0	0.00		2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
325318	\N	Mary	Beth Goldsmith	4612	4359	2025-06-24 19:48:53.831168-05	nndz-WkNDOHlMYjlnUT09	4513	t	\N	0	6	0.00		2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
325319	\N	Laura	Kepes	4612	4359	2025-06-24 19:48:53.831168-05	nndz-WkNDL3diLzZoUT09	4513	t	\N	2	6	25.00		2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
325320	\N	Julie	Radner	4612	4359	2025-06-24 19:48:53.831168-05	nndz-WkM2d3dybjloQT09	4513	t	\N	2	1	66.70		2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
325321	\N	Robyn	Rosenblatt	4612	4359	2025-06-24 19:48:53.831168-05	nndz-WkNDeHdiN3hoQT09	4513	t	\N	2	6	25.00		2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
325322	\N	Julie	Smith	4612	4359	2025-06-24 19:48:53.831168-05	nndz-WkMrNnc3ajRnQT09	4513	t	\N	3	4	42.90		2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
325323	\N	Liz	Agins	4612	4359	2025-06-24 19:48:53.831168-05	nndz-WkMrNnc3ajRnZz09	4513	t	\N	0	0	0.00		2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
325324	\N	Aly	Feder	4612	4359	2025-06-24 19:48:53.831168-05	nndz-WkNDL3diLzdqQT09	4513	t	\N	2	8	20.00		2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
325325	\N	Julia	Gerstein	4612	4359	2025-06-24 19:48:53.831168-05	nndz-WkM2eHlMZi9nUT09	4513	t	\N	0	6	0.00		2025-06-24 19:48:53.831168-05	0	0	0	0.00	\N
325326	\N	Abby	Eisenberg	4612	4359	2025-06-24 19:48:54.082673-05	nndz-WkM2eHg3YjVqUT09	4513	t	\N	1	8	11.10		2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
325327	\N	Terry	Kass	4612	4359	2025-06-24 19:48:54.082673-05	nndz-WkM2eHg3YjRoZz09	4513	t	\N	0	2	0.00		2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
325328	\N	Andrea	Kroll	4612	4359	2025-06-24 19:48:54.082673-05	nndz-WkNHNXliN3dqQT09	4513	t	\N	1	8	11.10		2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
325329	\N	Nadine	Sir	4618	4359	2025-06-24 19:48:54.082673-05	nndz-WkNDL3diNzRoQT09	4513	t	\N	4	3	57.10	C	2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
325330	\N	Leah	Wolfe	4618	4359	2025-06-24 19:48:54.082673-05	nndz-WkM2eHg3NzdqUT09	4513	t	\N	1	5	16.70	CC	2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
325331	\N	Kelly	Bontempo	4618	4359	2025-06-24 19:48:54.082673-05	nndz-WkM2eHg3aitndz09	4513	t	\N	7	3	70.00		2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
325332	\N	Amy	Breaux	4618	4359	2025-06-24 19:48:54.082673-05	nndz-WkNDL3diNzVnZz09	4513	t	\N	4	4	50.00		2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
325333	\N	Danielle	Hartung	4618	4359	2025-06-24 19:48:54.082673-05	nndz-WkNDL3diNzRqUT09	4513	t	\N	5	5	50.00		2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
325334	\N	Sara	Latreille	4618	4359	2025-06-24 19:48:54.082673-05	nndz-WkNDL3diL3doQT09	4513	t	\N	4	5	44.40		2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
325335	\N	Amanda	Miller	4618	4359	2025-06-24 19:48:54.082673-05	nndz-WkM2eHhycndqUT09	4513	t	\N	12	7	63.20		2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
325336	\N	Christie	Warren	4618	4359	2025-06-24 19:48:54.082673-05	nndz-WkNDL3diNzdnUT09	4513	t	\N	3	6	33.30		2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
325337	\N	Megan	Weber	4618	4359	2025-06-24 19:48:54.082673-05	nndz-WkNHN3hMbnhodz09	4513	t	\N	4	3	57.10		2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
325338	\N	Niloofar	Yousefi	4618	4359	2025-06-24 19:48:54.082673-05	nndz-WkM2eHdyM3hodz09	4513	t	\N	9	4	69.20		2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
325339	\N	Elizabeth	Eshoo	4618	4359	2025-06-24 19:48:54.082673-05	nndz-WkNHNXdyNy9ndz09	4513	t	\N	1	9	10.00		2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
325340	\N	Gina	Johnson	4618	4359	2025-06-24 19:48:54.082673-05	nndz-WkMrK3dicitodz09	4513	t	\N	12	2	85.70		2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
325341	\N	Brandy	Oomen	4618	4359	2025-06-24 19:48:54.082673-05	nndz-WkM2eHhydjVoUT09	4513	t	\N	3	1	75.00		2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
325342	\N	Tammy	Stachorek	4618	4359	2025-06-24 19:48:54.082673-05	nndz-WkM2d3g3djdoUT09	4513	t	\N	8	4	66.70		2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
325343	\N	Heiji	Choy Black	4631	4359	2025-06-24 19:48:54.082673-05	nndz-WkNDL3diejRnUT09	4513	t	\N	4	4	50.00	C	2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
325344	\N	Eileen	Murphy	4631	4359	2025-06-24 19:48:54.082673-05	nndz-WkNDOHlMYjVoZz09	4513	t	\N	2	4	33.30	CC	2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
325345	\N	Cynthia	Ballew	4631	4359	2025-06-24 19:48:54.082673-05	nndz-WkNDL3diLzVnUT09	4513	t	\N	0	2	0.00		2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
325346	\N	Candice	Dias	4631	4359	2025-06-24 19:48:54.082673-05	nndz-WkNHNXhiNzVndz09	4513	t	\N	0	6	0.00		2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
325347	\N	Joan	Hoese	4631	4359	2025-06-24 19:48:54.082673-05	nndz-WkNDOHlMMy9qQT09	4513	t	\N	3	4	42.90		2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
325348	\N	Debby	Krebs	4631	4359	2025-06-24 19:48:54.082673-05	nndz-WkNHN3hiditnUT09	4513	t	\N	2	0	100.00		2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
325349	\N	Lauren	Marker	4631	4359	2025-06-24 19:48:54.082673-05	nndz-WkM2d3c3M3dodz09	4513	t	\N	0	0	0.00		2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
325350	\N	Lisa	Nadler	4631	4359	2025-06-24 19:48:54.082673-05	nndz-WkNDOHlMMy9nUT09	4513	t	\N	3	1	75.00		2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
325351	\N	Abby	Phelps	4631	4359	2025-06-24 19:48:54.082673-05	nndz-WkNHNXhiNzVnUT09	4513	t	\N	5	4	55.60		2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
325352	\N	Carla	Sanchez-Palacios	4631	4359	2025-06-24 19:48:54.082673-05	nndz-WkNDL3diN3dnQT09	4513	t	\N	3	7	30.00		2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
325353	\N	Joanna	Sevim	4631	4359	2025-06-24 19:48:54.082673-05	nndz-WkNDL3diejRoZz09	4513	t	\N	1	6	14.30		2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
325354	\N	Megan	Tirpak	4631	4359	2025-06-24 19:48:54.082673-05	nndz-WkM2d3dMbnhqUT09	4513	t	\N	5	1	83.30		2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
325355	\N	Barbara	Potter	4631	4359	2025-06-24 19:48:54.082673-05	nndz-WkNDOHlMMy9oQT09	4513	t	\N	0	0	0.00		2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
325356	\N	Inna	Elterman	4631	4359	2025-06-24 19:48:54.082673-05	nndz-WkNDL3diLzVoZz09	4513	t	\N	7	2	77.80		2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
325357	\N	Kirste	Gaudet	4631	4359	2025-06-24 19:48:54.082673-05	nndz-WlNlNnlMYjdndz09	4513	t	\N	6	2	75.00		2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
325358	\N	Courtney	Johnson	4631	4359	2025-06-24 19:48:54.082673-05	nndz-WlNlOXhMZnhoUT09	4513	t	\N	4	0	100.00		2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
325359	\N	Laura	Smith	4637	4359	2025-06-24 19:48:54.082673-05	nndz-WkNDOHlMcjlqUT09	4513	t	\N	0	5	0.00	C	2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
325360	\N	Angie	Rover	4637	4359	2025-06-24 19:48:54.082673-05	nndz-WkNHNHlMejVqQT09	4513	t	\N	13	4	76.50	CC	2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
325361	\N	Katie	Beach	4637	4359	2025-06-24 19:48:54.082673-05	nndz-WkNHNXdMbjRnZz09	4513	t	\N	7	0	100.00		2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
325362	\N	Andrea	Johnson	4637	4359	2025-06-24 19:48:54.082673-05	nndz-WkM2eHg3bjlqUT09	4513	t	\N	0	3	0.00		2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
325363	\N	Maisie	Kunkel	4637	4359	2025-06-24 19:48:54.082673-05	nndz-WkMrNnc3ai9qQT09	4513	t	\N	3	3	50.00		2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
325364	\N	Francesca	Meder	4637	4359	2025-06-24 19:48:54.082673-05	nndz-WkNDL3dicjlnUT09	4513	t	\N	6	2	75.00		2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
325365	\N	Deb	Ponko	4637	4359	2025-06-24 19:48:54.082673-05	nndz-WkNDOHlMbnhqQT09	4513	t	\N	3	3	50.00		2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
325366	\N	Tracy	Sarbaugh	4637	4359	2025-06-24 19:48:54.082673-05	nndz-WkM2eHg3bjZoQT09	4513	t	\N	5	3	62.50		2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
325367	\N	Melissa	Uhlig	4637	4359	2025-06-24 19:48:54.082673-05	nndz-WkM2eHg3bjhnQT09	4513	t	\N	6	3	66.70		2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
325368	\N	Gia	Diakakis	4637	4359	2025-06-24 19:48:54.082673-05	nndz-WkM2eHg3bjdqUT09	4513	t	\N	15	5	75.00		2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
325369	\N	Kathryn	McGowan	4637	4359	2025-06-24 19:48:54.082673-05	nndz-WkMrK3hyM3hodz09	4513	t	\N	9	2	81.80		2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
325370	\N	Kelly	Hondru	4637	4359	2025-06-24 19:48:54.082673-05	nndz-WkM2eHg3bjZoUT09	4513	t	\N	7	3	70.00		2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
325371	\N	Liz	Robinson	4637	4359	2025-06-24 19:48:54.082673-05	nndz-WkM2eHhyandnUT09	4513	t	\N	10	6	62.50		2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
325372	\N	Jacki	Ruh	4637	4359	2025-06-24 19:48:54.082673-05	nndz-WkNDL3didnhqUT09	4513	t	\N	5	1	83.30		2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
325373	\N	Jennifer	Tucker	4637	4359	2025-06-24 19:48:54.082673-05	nndz-WkM2eHg3bjZqUT09	4513	t	\N	12	2	85.70		2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
325374	\N	Judy	Yoo	4637	4359	2025-06-24 19:48:54.082673-05	nndz-WkM2eHg3bjZqQT09	4513	t	\N	11	5	68.80		2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
325375	\N	Julie	Buranosky	4638	4359	2025-06-24 19:48:54.082673-05	nndz-WkNHNXc3dndoUT09	4513	t	\N	6	3	66.70	C	2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
325376	\N	Mary	Clare Johnson	4638	4359	2025-06-24 19:48:54.082673-05	nndz-WkNDOHlMcitndz09	4513	t	\N	5	2	71.40	CC	2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
325377	\N	Kelly	Albrecht	4638	4359	2025-06-24 19:48:54.082673-05	nndz-WkMrK3dydjZnZz09	4513	t	\N	5	2	71.40		2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
325378	\N	Bonnie	Duman	4638	4359	2025-06-24 19:48:54.082673-05	nndz-WkNDOHlMbnhoQT09	4513	t	\N	3	2	60.00		2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
325379	\N	Ally	Engel	4638	4359	2025-06-24 19:48:54.082673-05	nndz-WkM2eHhybjRnZz09	4513	t	\N	1	6	14.30		2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
325380	\N	Liz	Fauntleroy	4638	4359	2025-06-24 19:48:54.082673-05	nndz-WkNDOHlMcnhoQT09	4513	t	\N	3	3	50.00		2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
325381	\N	Julie	Ginn	4638	4359	2025-06-24 19:48:54.082673-05	nndz-WkNDOHlMYjRoUT09	4513	t	\N	4	3	57.10		2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
325382	\N	Jeannette	Samson	4638	4359	2025-06-24 19:48:54.082673-05	nndz-WkM2d3dMZjdoUT09	4513	t	\N	3	3	50.00		2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
325383	\N	Corey	Swender	4638	4359	2025-06-24 19:48:54.082673-05	nndz-WkNDOHlMZjdoUT09	4513	t	\N	3	3	50.00		2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
325384	\N	Melinda	Vajdic	4638	4359	2025-06-24 19:48:54.082673-05	nndz-WkNDL3diejdnUT09	4513	t	\N	2	5	28.60		2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
325385	\N	Kirsten	Whipple	4638	4359	2025-06-24 19:48:54.082673-05	nndz-WkNDOHlMbjdqQT09	4513	t	\N	3	3	50.00		2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
325386	\N	Roberta	Heintz	4569	4360	2025-06-24 19:48:54.082673-05	nndz-WkNHN3hicjdqQT09	4513	t	\N	6	7	46.20	C	2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
325387	\N	Amanda	Manczak	4569	4360	2025-06-24 19:48:54.082673-05	nndz-WkM2eHg3Znhndz09	4513	t	\N	6	3	66.70	CC	2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
325388	\N	Ellen	Adler	4569	4360	2025-06-24 19:48:54.082673-05	nndz-WkM2eHg3ZndoUT09	4513	t	\N	6	3	66.70		2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
325389	\N	Kristen	Bouchard	4569	4360	2025-06-24 19:48:54.082673-05	nndz-WkNHN3c3djloUT09	4513	t	\N	5	3	62.50		2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
325390	\N	Mary	Etherington	4569	4360	2025-06-24 19:48:54.082673-05	nndz-WkM2eHg3ZnhoQT09	4513	t	\N	5	0	100.00		2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
325391	\N	Kate	Fanselow	4569	4360	2025-06-24 19:48:54.082673-05	nndz-WkM2eHg3Znhodz09	4513	t	\N	10	6	62.50		2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
325392	\N	Jane	Hoffman	4569	4360	2025-06-24 19:48:54.082673-05	nndz-WkNDL3diendnQT09	4513	t	\N	5	2	71.40		2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
325393	\N	Dayna	Imhoff	4569	4360	2025-06-24 19:48:54.082673-05	nndz-WkNDOHlMbjhodz09	4513	t	\N	3	2	60.00		2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
325394	\N	Anne	Menke	4569	4360	2025-06-24 19:48:54.082673-05	nndz-WkM2eHg3ZnhnZz09	4513	t	\N	1	1	50.00		2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
325395	\N	Lesley	Olson	4569	4360	2025-06-24 19:48:54.082673-05	nndz-WkM2eHhyNzVodz09	4513	t	\N	7	3	70.00		2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
325396	\N	Alexis	Wormley	4569	4360	2025-06-24 19:48:54.082673-05	nndz-WkM2eHg3ZnhqQT09	4513	t	\N	6	2	75.00		2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
325397	\N	Katie	Karam	4569	4360	2025-06-24 19:48:54.082673-05	nndz-WkMreHhML3hqQT09	4513	t	\N	1	3	25.00		2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
325398	\N	Tiffany	Seely-Brown	4569	4360	2025-06-24 19:48:54.082673-05	nndz-WkMrK3hMbjlqUT09	4513	t	\N	5	1	83.30		2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
325399	\N	Simone	Zorzy	4569	4360	2025-06-24 19:48:54.082673-05	nndz-WkMrK3hMajlqQT09	4513	t	\N	8	2	80.00		2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
325400	\N	Julia	Wold	4595	4360	2025-06-24 19:48:54.082673-05	nndz-WkM2eHg3N3hoZz09	4513	t	\N	0	7	0.00	C	2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
325401	\N	Kiersten	Litzsinger	4595	4360	2025-06-24 19:48:54.082673-05	nndz-WkNHNXdMM3dqQT09	4513	t	\N	6	1	85.70	CC	2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
325402	\N	Brook	Bayly	4595	4360	2025-06-24 19:48:54.082673-05	nndz-WkNHNXdMM3dndz09	4513	t	\N	5	4	55.60		2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
325403	\N	Beth	Cummins	4595	4360	2025-06-24 19:48:54.082673-05	nndz-WkNDL3diLy9nQT09	4513	t	\N	0	0	0.00		2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
325404	\N	Kim	Galvin	4595	4360	2025-06-24 19:48:54.082673-05	nndz-WkNDL3diLzhoZz09	4513	t	\N	4	4	50.00		2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
325405	\N	Holly	Heitman	4595	4360	2025-06-24 19:48:54.082673-05	nndz-WkNDOHlMYjZnZz09	4513	t	\N	0	5	0.00		2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
325406	\N	Susan	Loiacano	4595	4360	2025-06-24 19:48:54.082673-05	nndz-WkNHNXdMM3hqUT09	4513	t	\N	4	4	50.00		2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
325407	\N	Janet	Page	4595	4360	2025-06-24 19:48:54.082673-05	nndz-WkNDOHlMbnhnZz09	4513	t	\N	0	0	0.00		2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
325408	\N	Fiona	Partington	4595	4360	2025-06-24 19:48:54.082673-05	nndz-WkNDL3diMzdnUT09	4513	t	\N	0	0	0.00		2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
325409	\N	Liz	Alkon	4595	4360	2025-06-24 19:48:54.082673-05	nndz-WkM2eHg3ejZqUT09	4513	t	\N	6	1	85.70		2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
325410	\N	Nisha	York	4595	4360	2025-06-24 19:48:54.082673-05	nndz-WkNHN3diMzdnQT09	4513	t	\N	7	1	87.50		2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
325411	\N	Simone	Asmussen	4595	4360	2025-06-24 19:48:54.082673-05	nndz-WkNHNXdMM3hnQT09	4513	t	\N	0	2	0.00		2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
325412	\N	Erin	Bearman	4595	4360	2025-06-24 19:48:54.082673-05	nndz-WkM2eHhyejlnZz09	4513	t	\N	9	3	75.00		2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
325413	\N	Julie	Carter	4595	4360	2025-06-24 19:48:54.082673-05	nndz-WkNHNXdMM3hndz09	4513	t	\N	4	3	57.10		2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
325414	\N	Heidi	Clifton	4595	4360	2025-06-24 19:48:54.082673-05	nndz-WkNDOHlMZjVoQT09	4513	t	\N	6	4	60.00		2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
325415	\N	Kristen	Esplin	4595	4360	2025-06-24 19:48:54.082673-05	nndz-WkNDL3dicjZqUT09	4513	t	\N	3	5	37.50		2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
325416	\N	Tammy	Fiordaliso	4595	4360	2025-06-24 19:48:54.082673-05	nndz-WkNDL3diL3dnZz09	4513	t	\N	5	1	83.30		2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
325417	\N	Maggie	Fishbune	4595	4360	2025-06-24 19:48:54.082673-05	nndz-WkM2d3hyNzdodz09	4513	t	\N	6	0	100.00		2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
325418	\N	Joan	Giangiorgi	4595	4360	2025-06-24 19:48:54.082673-05	nndz-WkNDL3dicjZnZz09	4513	t	\N	2	1	66.70		2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
325419	\N	Lynn	Jensen	4595	4360	2025-06-24 19:48:54.082673-05	nndz-WkNHNXdMcjVoUT09	4513	t	\N	3	3	50.00		2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
325420	\N	Susan	McMahon	4595	4360	2025-06-24 19:48:54.082673-05	nndz-WkNHNXdMcjVoQT09	4513	t	\N	4	5	44.40		2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
325421	\N	Christine	Moore	4595	4360	2025-06-24 19:48:54.082673-05	nndz-WkM2eHlMci9oQT09	4513	t	\N	5	2	71.40		2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
325422	\N	Julie	Ward	4595	4360	2025-06-24 19:48:54.082673-05	nndz-WkNDL3diL3dnUT09	4513	t	\N	4	3	57.10		2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
325423	\N	Connie	Moran	4608	4360	2025-06-24 19:48:54.082673-05	nndz-WkNHNXdMcndndz09	4513	t	\N	7	2	77.80	C	2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
325424	\N	Stephanie	Broadhurst	4608	4360	2025-06-24 19:48:54.082673-05	nndz-WkNDL3didnhndz09	4513	t	\N	1	3	25.00	CC	2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
325425	\N	Stephanie	Eiden	4608	4360	2025-06-24 19:48:54.082673-05	nndz-WkNHNXdMci9nZz09	4513	t	\N	6	3	66.70		2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
325426	\N	Valerie	Gaines	4608	4360	2025-06-24 19:48:54.082673-05	nndz-WkM2eHg3anhnUT09	4513	t	\N	9	8	52.90		2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
325427	\N	Maddie	Knowland	4608	4360	2025-06-24 19:48:54.082673-05	nndz-WkM2eHg3ejdqQT09	4513	t	\N	6	3	66.70		2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
325428	\N	Lynne	Terry	4608	4360	2025-06-24 19:48:54.082673-05	nndz-WkNDOHlMYjdoUT09	4513	t	\N	0	2	0.00		2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
325429	\N	Kristin	Alcala	4608	4360	2025-06-24 19:48:54.082673-05	nndz-WkNHNXdMcndodz09	4513	t	\N	13	4	76.50		2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
325430	\N	Simone	O'Rear	4608	4360	2025-06-24 19:48:54.082673-05	nndz-WkM2eHg3ejZoUT09	4513	t	\N	6	2	75.00		2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
325431	\N	Amy	Peters - MSC	4608	4360	2025-06-24 19:48:54.082673-05	nndz-WkM2eHhycjRodz09	4513	t	\N	14	4	77.80		2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
325432	\N	Mandy	Breaker	4608	4360	2025-06-24 19:48:54.082673-05	nndz-WkM2eHhyM3hqQT09	4513	t	\N	2	8	20.00		2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
325433	\N	Courtney	Cook	4608	4360	2025-06-24 19:48:54.082673-05	nndz-WkM2eHg3ajlodz09	4513	t	\N	1	11	8.30		2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
325434	\N	Liz	Licata	4608	4360	2025-06-24 19:48:54.082673-05	nndz-WkM2eHlicjloQT09	4513	t	\N	1	7	12.50		2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
325435	\N	Annie	Miskella	4608	4360	2025-06-24 19:48:54.082673-05	nndz-WkNDL3diajVqQT09	4513	t	\N	4	8	33.30		2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
325436	\N	Shannon	Page	4608	4360	2025-06-24 19:48:54.082673-05	nndz-WkM2eHhyM3doQT09	4513	t	\N	3	3	50.00		2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
325437	\N	Kathy	Ryan	4608	4360	2025-06-24 19:48:54.082673-05	nndz-WkM2eHlicjlnQT09	4513	t	\N	5	10	33.30		2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
325438	\N	Jenny	Sloan	4608	4360	2025-06-24 19:48:54.082673-05	nndz-WkM2eHliNzRnQT09	4513	t	\N	5	4	55.60		2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
325439	\N	Tracey	Sartino	4610	4360	2025-06-24 19:48:54.082673-05	nndz-WkNDOHlMYi9oQT09	4513	t	\N	4	4	50.00	C	2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
325440	\N	Michele	Berman	4610	4360	2025-06-24 19:48:54.082673-05	nndz-WlNlNnhMdjdoUT09	4513	t	\N	1	2	33.30		2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
325441	\N	Morgan	Carr	4610	4360	2025-06-24 19:48:54.082673-05	nndz-WlNlN3dMbndqQT09	4513	t	\N	2	2	50.00		2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
325442	\N	MIchelle	Landry	4610	4360	2025-06-24 19:48:54.082673-05	nndz-WkNDeHdiN3dodz09	4513	t	\N	2	0	100.00		2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
325443	\N	Christine	Mahoney	4610	4360	2025-06-24 19:48:54.082673-05	nndz-WkNDOHlMYi9qUT09	4513	t	\N	2	5	28.60		2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
325444	\N	Elaine	Ni	4610	4360	2025-06-24 19:48:54.082673-05	nndz-WlNlN3g3cjRnUT09	4513	t	\N	7	10	41.20		2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
325445	\N	Jiyeon	Owens	4610	4360	2025-06-24 19:48:54.082673-05	nndz-WkNDOHlMYi9oUT09	4513	t	\N	4	2	66.70		2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
325446	\N	Jaye	Schreier	4610	4360	2025-06-24 19:48:54.082673-05	nndz-WkNDOHlMbjRodz09	4513	t	\N	4	3	57.10		2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
325447	\N	Heike	Spahn	4610	4360	2025-06-24 19:48:54.082673-05	nndz-WlNlN3g3cjRnQT09	4513	t	\N	1	0	100.00		2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
325448	\N	Maura	Starshak	4610	4360	2025-06-24 19:48:54.082673-05	nndz-WkMrNnc3djlnUT09	4513	t	\N	2	4	33.30		2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
325449	\N	Mary	Truong	4610	4360	2025-06-24 19:48:54.082673-05	nndz-WkM2eHhycjlqQT09	4513	t	\N	4	3	57.10		2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
325450	\N	Laurie	Redman	4610	4360	2025-06-24 19:48:54.082673-05	nndz-WkNDOHlMMytoUT09	4513	t	\N	3	7	30.00		2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
325451	\N	Melissa	Schopin	4610	4360	2025-06-24 19:48:54.082673-05	nndz-WlNlN3g3cjRoZz09	4513	t	\N	6	4	60.00		2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
325452	\N	Krista	Blazek Hogarth	4610	4360	2025-06-24 19:48:54.082673-05	nndz-WkM2eHhycjlodz09	4513	t	\N	4	3	57.10		2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
325453	\N	Sarah	Jamieson	4610	4360	2025-06-24 19:48:54.082673-05	nndz-WlNlN3g3cjdoUT09	4513	t	\N	3	1	75.00		2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
325454	\N	Katie	Baisley	4611	4360	2025-06-24 19:48:54.082673-05	nndz-WkM2eHhMZnhodz09	4513	t	\N	6	5	54.50	C	2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
325455	\N	Alison	Beitzel	4611	4360	2025-06-24 19:48:54.082673-05	nndz-WkNDL3diM3doUT09	4513	t	\N	3	5	37.50		2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
325456	\N	Lynn	Bruno	4611	4360	2025-06-24 19:48:54.082673-05	nndz-WkNDL3diejdqUT09	4513	t	\N	3	4	42.90		2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
325457	\N	Patty	Buckingham	4611	4360	2025-06-24 19:48:54.082673-05	nndz-WkNDOHlMei9oUT09	4513	t	\N	2	7	22.20		2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
325458	\N	Dinny	Dwyer	4611	4360	2025-06-24 19:48:54.082673-05	nndz-WkNDOHlMejlnUT09	4513	t	\N	1	6	14.30		2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
325459	\N	Missy	Lafferty	4611	4360	2025-06-24 19:48:54.082673-05	nndz-WkNDOHlMYndoQT09	4513	t	\N	3	5	37.50		2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
325460	\N	Dianne	Larsen	4611	4360	2025-06-24 19:48:54.082673-05	nndz-WkNDL3diM3hqQT09	4513	t	\N	1	6	14.30		2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
325461	\N	Megan	Piazza	4611	4360	2025-06-24 19:48:54.082673-05	nndz-WkMrNnc3djlndz09	4513	t	\N	2	3	40.00		2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
325462	\N	Meredith	Richard	4611	4360	2025-06-24 19:48:54.082673-05	nndz-WkNDL3dicjVqQT09	4513	t	\N	1	7	12.50		2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
325463	\N	Kari	McNeil	4611	4360	2025-06-24 19:48:54.082673-05	nndz-WkNDOHlMYndnQT09	4513	t	\N	5	4	55.60		2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
325464	\N	Laurie	Hamman	4635	4360	2025-06-24 19:48:54.082673-05	nndz-WkNDL3diMzhodz09	4513	t	\N	3	4	42.90	C	2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
325465	\N	Lisa	Hague	4635	4360	2025-06-24 19:48:54.082673-05	nndz-WkNDOHlMM3dodz09	4513	t	\N	4	2	66.70	CC	2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
325466	\N	Stephanie	Barry	4635	4360	2025-06-24 19:48:54.082673-05	nndz-WkNDL3diejlnZz09	4513	t	\N	2	4	33.30		2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
325467	\N	Heather	Bartell	4635	4360	2025-06-24 19:48:54.082673-05	nndz-WkNDL3diN3doUT09	4513	t	\N	3	3	50.00		2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
325468	\N	Lauren	Edelston	4635	4360	2025-06-24 19:48:54.082673-05	nndz-WkMrK3dMdjlnQT09	4513	t	\N	2	5	28.60		2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
325469	\N	Colleen	Meyers	4635	4360	2025-06-24 19:48:54.082673-05	nndz-WkNDL3diMzhoZz09	4513	t	\N	6	1	85.70		2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
325470	\N	Stephanie	Miller	4635	4360	2025-06-24 19:48:54.082673-05	nndz-WkNDL3dicjdoUT09	4513	t	\N	4	2	66.70		2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
325471	\N	Julie	Pagliaro	4635	4360	2025-06-24 19:48:54.082673-05	nndz-WkNDL3diN3hqQT09	4513	t	\N	6	2	75.00		2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
325472	\N	Karin	Palasz	4635	4360	2025-06-24 19:48:54.082673-05	nndz-WkNDOHlMajloQT09	4513	t	\N	4	1	80.00		2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
325473	\N	Debbie	Perkins	4635	4360	2025-06-24 19:48:54.082673-05	nndz-WkNDOHlMM3dndz09	4513	t	\N	5	1	83.30		2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
325474	\N	Evelyn	Vlahandreas	4635	4360	2025-06-24 19:48:54.082673-05	nndz-WkNDOHlMM3hoUT09	4513	t	\N	2	4	33.30		2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
325475	\N	Sherri	Zion	4635	4360	2025-06-24 19:48:54.082673-05	nndz-WkNDL3diendoZz09	4513	t	\N	0	0	0.00		2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
325476	\N	Kristin	Kavanagh	4635	4360	2025-06-24 19:48:54.082673-05	nndz-WkM2eHhyai9oQT09	4513	t	\N	3	4	42.90		2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
325477	\N	Laura	Margolis	4635	4360	2025-06-24 19:48:54.082673-05	nndz-WkMrK3diZndodz09	4513	t	\N	6	3	66.70		2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
325478	\N	Heather	Wojteczko	4635	4360	2025-06-24 19:48:54.082673-05	nndz-WkM2d3c3bjlodz09	4513	t	\N	9	3	75.00		2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
325479	\N	Cynthia	Reeder	4639	4360	2025-06-24 19:48:54.082673-05	nndz-WkM2eHg3LzlnUT09	4513	t	\N	4	6	40.00	C	2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
325480	\N	Megan	Spathis	4639	4360	2025-06-24 19:48:54.082673-05	nndz-WkM2eHdyM3hoZz09	4513	t	\N	4	5	44.40	CC	2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
325481	\N	Erin	L Burke	4639	4360	2025-06-24 19:48:54.082673-05	nndz-WkNDL3diLzVqQT09	4513	t	\N	4	3	57.10		2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
325482	\N	Mary	Campobasso	4639	4360	2025-06-24 19:48:54.082673-05	nndz-WkNDL3diN3doZz09	4513	t	\N	2	2	50.00		2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
325483	\N	Lorri	Collins	4639	4360	2025-06-24 19:48:54.082673-05	nndz-WkNDOHlMbjRnUT09	4513	t	\N	6	2	75.00		2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
325484	\N	Christin	Eggener	4639	4360	2025-06-24 19:48:54.082673-05	nndz-WkM2eHhyYitndz09	4513	t	\N	5	0	100.00		2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
325485	\N	Katie	Hughes	4639	4360	2025-06-24 19:48:54.082673-05	nndz-WkNDL3diLzVnQT09	4513	t	\N	6	1	85.70		2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
325486	\N	Rachel	Bowlin	4639	4360	2025-06-24 19:48:54.082673-05	nndz-WkM2eHhyYi9nUT09	4513	t	\N	8	3	72.70		2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
325487	\N	Pam	Hartigan	4639	4360	2025-06-24 19:48:54.082673-05	nndz-WkNDOHlMcnhqQT09	4513	t	\N	4	3	57.10		2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
325488	\N	Nora	Waryas	4639	4360	2025-06-24 19:48:54.082673-05	nndz-WkM2eHhyYjZoQT09	4513	t	\N	8	5	61.50		2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
325489	\N	Sue	Fasciano	4639	4360	2025-06-24 19:48:54.082673-05	nndz-WkNDOHlMcndqUT09	4513	t	\N	0	0	0.00		2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
325490	\N	Kelly	Brown	4639	4360	2025-06-24 19:48:54.082673-05	nndz-WkNHNHdiYjZnQT09	4513	t	\N	3	5	37.50		2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
325491	\N	Meghan	Decker	4639	4360	2025-06-24 19:48:54.082673-05	nndz-WkMrK3dyci9oUT09	4513	t	\N	5	3	62.50		2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
325492	\N	Katy	Klemmer	4642	4361	2025-06-24 19:48:54.082673-05	nndz-WkNHNHlMditnUT09	4513	t	\N	6	3	66.70	C	2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
325493	\N	Karen	O'Brien	4642	4361	2025-06-24 19:48:54.082673-05	nndz-WkNHNXdyLytoZz09	4513	t	\N	5	4	55.60	CC	2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
325494	\N	Lydia	DeLeo	4642	4361	2025-06-24 19:48:54.082673-05	nndz-WkNDOHlMYjlqQT09	4513	t	\N	3	2	60.00		2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
325495	\N	Amy	Eccleston	4642	4361	2025-06-24 19:48:54.082673-05	nndz-WkNHNXhiN3dodz09	4513	t	\N	2	3	40.00		2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
325496	\N	Mickey	Franson	4642	4361	2025-06-24 19:48:54.082673-05	nndz-WkNDOHlMNy9qQT09	4513	t	\N	0	3	0.00		2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
325497	\N	Tricia	Gartz	4642	4361	2025-06-24 19:48:54.082673-05	nndz-WkNDL3diNzhnZz09	4513	t	\N	3	5	37.50		2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
325498	\N	Lauren	Trankina	4642	4361	2025-06-24 19:48:54.082673-05	nndz-WkM2eHhyajVqQT09	4513	t	\N	1	5	16.70		2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
325499	\N	Colleen	Washburn	4642	4361	2025-06-24 19:48:54.082673-05	nndz-WkNDOHlMdi9nQT09	4513	t	\N	5	1	83.30		2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
325500	\N	Lauren	Kane	4642	4361	2025-06-24 19:48:54.082673-05	nndz-WkM2eHhMYi9oUT09	4513	t	\N	8	4	66.70		2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
325501	\N	Liz	Krupkin	4642	4361	2025-06-24 19:48:54.082673-05	nndz-WkNHNHlMcjVoQT09	4513	t	\N	7	5	58.30		2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
325502	\N	Melissa	Koss	4642	4361	2025-06-24 19:48:54.082673-05	nndz-WkMrK3hiZjdqQT09	4513	t	\N	19	5	79.20		2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
325503	\N	Laura	Pine	4642	4361	2025-06-24 19:48:54.082673-05	nndz-WkMrK3lMenhqUT09	4513	t	\N	2	5	28.60		2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
325504	\N	Stacey	Burke	4642	4362	2025-06-24 19:48:54.082673-05	nndz-WkM2eHliNzVnQT09	4513	t	\N	3	6	33.30	C	2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
325505	\N	Elizabeth	Jensen	4642	4362	2025-06-24 19:48:54.082673-05	nndz-WkNHNXdyZitoQT09	4513	t	\N	6	6	50.00	CC	2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
325506	\N	Allison	Becker	4642	4362	2025-06-24 19:48:54.082673-05	nndz-WkM2eHliNzVodz09	4513	t	\N	7	7	50.00		2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
325507	\N	Amanda	Dauten	4642	4362	2025-06-24 19:48:54.082673-05	nndz-WlNlN3dMNzhoZz09	4513	t	\N	5	3	62.50		2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
325508	\N	Amy	Glynn	4642	4362	2025-06-24 19:48:54.082673-05	nndz-WkNHNXdyZitnQT09	4513	t	\N	7	4	63.60		2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
325509	\N	Amy	Graham	4642	4362	2025-06-24 19:48:54.082673-05	nndz-WkNDOHlMYi9nUT09	4513	t	\N	1	4	20.00		2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
325510	\N	Helen	Kim	4642	4362	2025-06-24 19:48:54.082673-05	nndz-WkNHNXlMMzZoQT09	4513	t	\N	0	6	0.00		2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
325511	\N	Sue	Pelzek	4642	4362	2025-06-24 19:48:54.082673-05	nndz-WkM2eHg3LzlqQT09	4513	t	\N	2	4	33.30		2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
325512	\N	Lesa	Rizzolo	4642	4362	2025-06-24 19:48:54.082673-05	nndz-WkNDOHlMLy9odz09	4513	t	\N	1	6	14.30		2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
325513	\N	Jenine	Tubergen	4642	4362	2025-06-24 19:48:54.082673-05	nndz-WkNHNXdyZjZoZz09	4513	t	\N	4	4	50.00		2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
325514	\N	Melissa	Koss	4642	4362	2025-06-24 19:48:54.082673-05	nndz-WkMrK3hiZjdqQT09	4513	t	\N	19	5	79.20		2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
325515	\N	Maria	Parmentier	4642	4362	2025-06-24 19:48:54.082673-05	nndz-WkM2eHliNzhnUT09	4513	t	\N	10	7	58.80		2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
325516	\N	Candice	Stepan	4646	4360	2025-06-24 19:48:54.082673-05	nndz-WkNHN3dMbjZndz09	4513	t	\N	2	6	25.00	C	2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
325517	\N	Ellen	Castellini	4646	4360	2025-06-24 19:48:54.082673-05	nndz-WkMrN3g3ajRqQT09	4513	t	\N	8	7	53.30	CC	2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
325518	\N	Kim	Knaus	4646	4360	2025-06-24 19:48:54.082673-05	nndz-WkNDOHlMM3doZz09	4513	t	\N	2	6	25.00		2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
325519	\N	Michel	Mahaffey	4646	4360	2025-06-24 19:48:54.082673-05	nndz-WkNDOHlMYjlnQT09	4513	t	\N	2	6	25.00		2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
325520	\N	Kerri	Melzl	4646	4360	2025-06-24 19:48:54.082673-05	nndz-WkNHNXdyLzhnQT09	4513	t	\N	2	8	20.00		2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
325521	\N	Diane	Noth	4646	4360	2025-06-24 19:48:54.082673-05	nndz-WkNDK3lMZjlnUT09	4513	t	\N	2	8	20.00		2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
325522	\N	Kathy	Pagano	4646	4360	2025-06-24 19:48:54.082673-05	nndz-WkNDL3diN3dnZz09	4513	t	\N	2	5	28.60		2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
325523	\N	Judy	Piccione	4646	4360	2025-06-24 19:48:54.082673-05	nndz-WkNDOHlMYjhndz09	4513	t	\N	0	9	0.00		2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
325524	\N	Betsy	Weitzman	4646	4360	2025-06-24 19:48:54.082673-05	nndz-WkNDOHlMYjhoZz09	4513	t	\N	1	7	12.50		2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
325525	\N	Jen	Trzebiatowski	4646	4360	2025-06-24 19:48:54.082673-05	nndz-WkMrK3dMMy9oZz09	4513	t	\N	8	10	44.40		2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
325526	\N	Meg	Zuehl	4646	4360	2025-06-24 19:48:54.082673-05	nndz-WkM2d3hidnhqQT09	4513	t	\N	10	6	62.50		2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
325527	\N	Jennifer	Markman	4571	4363	2025-06-24 19:48:54.082673-05	nndz-WkM2eHg3cndnQT09	4513	t	\N	7	2	77.80	C	2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
325528	\N	Marissa	Been	4571	4363	2025-06-24 19:48:54.082673-05	nndz-WkNDL3diMzlndz09	4513	t	\N	1	5	16.70		2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
325529	\N	Sara	Block	4571	4363	2025-06-24 19:48:54.082673-05	nndz-WkNDL3diMzZoUT09	4513	t	\N	1	5	16.70		2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
325530	\N	Jennifer	Engelman	4571	4363	2025-06-24 19:48:54.082673-05	nndz-WkNDL3diMzZnUT09	4513	t	\N	6	5	54.50		2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
325531	\N	Tracy	Feldman	4571	4363	2025-06-24 19:48:54.082673-05	nndz-WkNHNXdyejRnQT09	4513	t	\N	3	4	42.90		2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
325532	\N	Marilyn	Johnson	4571	4363	2025-06-24 19:48:54.082673-05	nndz-WkNDOHlMM3doQT09	4513	t	\N	2	4	33.30		2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
325533	\N	Karen	Ury	4571	4363	2025-06-24 19:48:54.082673-05	nndz-WkM2eHg3ejZndz09	4513	t	\N	3	3	50.00		2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
325534	\N	Karen	Lothan	4571	4363	2025-06-24 19:48:54.082673-05	nndz-WkNDL3diejdodz09	4513	t	\N	3	6	33.30		2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
325535	\N	Melissa	Rubenstein	4571	4363	2025-06-24 19:48:54.082673-05	nndz-WkNDL3diMzdndz09	4513	t	\N	2	6	25.00		2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
325536	\N	Dara	Weil	4571	4363	2025-06-24 19:48:54.082673-05	nndz-WkNDL3diMzZqUT09	4513	t	\N	3	5	37.50		2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
325537	\N	Jennifer	Fisher	4571	4363	2025-06-24 19:48:54.082673-05	nndz-WkNHNXdyejlqUT09	4513	t	\N	6	5	54.50		2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
325538	\N	Jody	Rotblatt	4571	4363	2025-06-24 19:48:54.082673-05	nndz-WkM2eHhMZitoQT09	4513	t	\N	0	1	0.00		2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
325539	\N	Heidi	Sachs	4571	4363	2025-06-24 19:48:54.082673-05	nndz-WkM2eHhyNzRndz09	4513	t	\N	7	4	63.60		2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
325540	\N	Roberta	Goodman	4571	4363	2025-06-24 19:48:54.082673-05	nndz-WkNDOHlMYjRqUT09	4513	t	\N	1	2	33.30		2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
325541	\N	Kylie	Hughes	4579	4363	2025-06-24 19:48:54.082673-05	nndz-WkM2eHg3cndqUT09	4513	t	\N	5	2	71.40	C	2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
325542	\N	Martha	Idler	4579	4363	2025-06-24 19:48:54.082673-05	nndz-WkNDL3diMzhoQT09	4513	t	\N	1	2	33.30	CC	2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
325543	\N	Colleen	MacKimm	4579	4363	2025-06-24 19:48:54.082673-05	nndz-WkNDL3didjVoUT09	4513	t	\N	4	1	80.00		2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
325544	\N	Nancy	McLaughlin	4579	4363	2025-06-24 19:48:54.082673-05	nndz-WkNDL3diLytndz09	4513	t	\N	0	1	0.00		2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
325545	\N	Susie	McMonagle	4579	4363	2025-06-24 19:48:54.082673-05	nndz-WkNDL3diMzhnUT09	4513	t	\N	1	1	50.00		2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
325546	\N	Kim	Peters	4579	4363	2025-06-24 19:48:54.082673-05	nndz-WkM2eHhyNzlnQT09	4513	t	\N	5	2	71.40		2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
325547	\N	Kim	Simon	4579	4363	2025-06-24 19:48:54.082673-05	nndz-WkNDL3diMzZoQT09	4513	t	\N	5	3	62.50		2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
325548	\N	Erin	Donohoe	4579	4363	2025-06-24 19:48:54.082673-05	nndz-WkM2eHg3cndnZz09	4513	t	\N	2	7	22.20		2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
325549	\N	Laura	Durkin	4579	4363	2025-06-24 19:48:54.082673-05	nndz-WkNDOHlMZjdnQT09	4513	t	\N	4	1	80.00		2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
325550	\N	Nicole	Goven	4579	4363	2025-06-24 19:48:54.082673-05	nndz-WkNHNXc3dndoZz09	4513	t	\N	7	4	63.60		2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
325551	\N	Lexi	Marietti	4579	4363	2025-06-24 19:48:54.082673-05	nndz-WkM2eHhyNytnZz09	4513	t	\N	7	2	77.80		2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
325552	\N	Jamie	Mauceri	4579	4363	2025-06-24 19:48:54.082673-05	nndz-WkM2eHhyNzlqUT09	4513	t	\N	7	2	77.80		2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
325553	\N	Allison	Angeloni	4579	4363	2025-06-24 19:48:54.082673-05	nndz-WkM2eHhyN3dnUT09	4513	t	\N	6	6	50.00		2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
325554	\N	Liz	Barnett	4579	4363	2025-06-24 19:48:54.082673-05	nndz-WkMrK3diei9oZz09	4513	t	\N	5	3	62.50		2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
325555	\N	Larissa	Kins	4579	4363	2025-06-24 19:48:54.082673-05	nndz-WkMrK3dyLzhnQT09	4513	t	\N	3	2	60.00		2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
325556	\N	Kelly	Monahan	4579	4363	2025-06-24 19:48:54.082673-05	nndz-WkMrL3lMandnQT09	4513	t	\N	6	1	85.70		2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
325557	\N	Stephanie	Muno	4579	4363	2025-06-24 19:48:54.082673-05	nndz-WkM2eHhyNzlqQT09	4513	t	\N	5	3	62.50		2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
325558	\N	Anne	Murdoch	4579	4363	2025-06-24 19:48:54.082673-05	nndz-WkM2eHhyNzhnUT09	4513	t	\N	6	3	66.70		2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
325559	\N	Janel	Palm	4579	4363	2025-06-24 19:48:54.082673-05	nndz-WkNDL3diMzhqQT09	4513	t	\N	4	4	50.00		2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
325560	\N	Peggy	Tarkington	4585	4363	2025-06-24 19:48:54.082673-05	nndz-WkNDL3diejZnZz09	4513	t	\N	0	5	0.00	C	2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
325561	\N	Danielle	Cupps	4585	4363	2025-06-24 19:48:54.082673-05	nndz-WlNhOXhiZjhndz09	4513	t	\N	1	7	12.50	CC	2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
325562	\N	Kara	Brittingham	4585	4363	2025-06-24 19:48:54.082673-05	nndz-WkNDOHlMYitoZz09	4513	t	\N	0	0	0.00		2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
325563	\N	Laura	Carriglio	4585	4363	2025-06-24 19:48:54.082673-05	nndz-WkNDOHlMYitqUT09	4513	t	\N	1	4	20.00		2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
325564	\N	Maren	Deaver	4585	4363	2025-06-24 19:48:54.082673-05	nndz-WkM2eHg3ajZnUT09	4513	t	\N	2	3	40.00		2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
325565	\N	Kim	Hack	4585	4363	2025-06-24 19:48:54.082673-05	nndz-WkNDL3diMzVoUT09	4513	t	\N	0	5	0.00		2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
325566	\N	Kathleen	Klaeser	4585	4363	2025-06-24 19:48:54.082673-05	nndz-WkNDOHlMajdnUT09	4513	t	\N	6	3	66.70		2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
325567	\N	Christy	Kyhl	4585	4363	2025-06-24 19:48:54.082673-05	nndz-WlNhNnliMzRoZz09	4513	t	\N	0	3	0.00		2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
325568	\N	Laurie	Landman	4585	4363	2025-06-24 19:48:54.082673-05	nndz-WkNDL3diejloQT09	4513	t	\N	6	2	75.00		2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
325569	\N	Susie	Mackenzie	4585	4363	2025-06-24 19:48:54.082673-05	nndz-WkM2eHg3ajZndz09	4513	t	\N	0	7	0.00		2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
325570	\N	Cindy	Polayes	4585	4363	2025-06-24 19:48:54.082673-05	nndz-WkNDOHlMYitqQT09	4513	t	\N	1	5	16.70		2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
325571	\N	Bridget	Rahr	4585	4363	2025-06-24 19:48:54.082673-05	nndz-WkNHNXhiZitoZz09	4513	t	\N	2	4	33.30		2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
325572	\N	Mimi	Brault	4585	4363	2025-06-24 19:48:54.082673-05	nndz-WkM2d3hiZitoQT09	4513	t	\N	0	0	0.00		2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
325573	\N	Laura	Eckert	4585	4363	2025-06-24 19:48:54.082673-05	nndz-WlNlNnhiNzlnQT09	4513	t	\N	0	0	0.00		2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
325574	\N	Lauren	Dupont	4585	4363	2025-06-24 19:48:54.082673-05	nndz-WkM2eHhyLytoQT09	4513	t	\N	5	4	55.60		2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
325575	\N	Lisa	Grady	4585	4363	2025-06-24 19:48:54.082673-05	nndz-WlNlNnlMejlndz09	4513	t	\N	4	3	57.10		2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
325576	\N	Shanley	Henry	4585	4363	2025-06-24 19:48:54.082673-05	nndz-WkMrK3hMLzZoUT09	4513	t	\N	9	5	64.30		2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
325577	\N	Caroline	Kinahan	4585	4363	2025-06-24 19:48:54.082673-05	nndz-WkM2eHhyLytnQT09	4513	t	\N	12	1	92.30		2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
325578	\N	Julie	Fleetwood	4608	4363	2025-06-24 19:48:54.082673-05	nndz-WkM2eHg3ejdqUT09	4513	t	\N	2	7	22.20	C	2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
325579	\N	Ginny	George	4608	4363	2025-06-24 19:48:54.082673-05	nndz-WkNDOHlMZitndz09	4513	t	\N	1	5	16.70	CC	2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
325580	\N	Courtney	Cook	4608	4363	2025-06-24 19:48:54.082673-05	nndz-WkM2eHg3ajlodz09	4513	t	\N	1	11	8.30		2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
325581	\N	Erica	Cordier	4608	4363	2025-06-24 19:48:54.082673-05	nndz-WkM2eHg3ajloZz09	4513	t	\N	5	4	55.60		2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
325582	\N	Kim	Donohoe	4608	4363	2025-06-24 19:48:54.082673-05	nndz-WkNDL3diejhndz09	4513	t	\N	0	2	0.00		2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
325583	\N	Liz	Licata	4608	4363	2025-06-24 19:48:54.082673-05	nndz-WkM2eHlicjloQT09	4513	t	\N	1	7	12.50		2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
325584	\N	Anne	Malone	4608	4363	2025-06-24 19:48:54.082673-05	nndz-WkNDOHlMZjloUT09	4513	t	\N	2	3	40.00		2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
325585	\N	Jocelyn	Shook	4608	4363	2025-06-24 19:48:54.082673-05	nndz-WkM2eHg3ajlnQT09	4513	t	\N	8	5	61.50		2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
325586	\N	Kellen	Spadafore	4608	4363	2025-06-24 19:48:54.082673-05	nndz-WkM2d3g3bi9nZz09	4513	t	\N	2	3	40.00		2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
325587	\N	Betsy	Vankula	4608	4363	2025-06-24 19:48:54.082673-05	nndz-WkM2eHhycjRoZz09	4513	t	\N	2	5	28.60		2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
325588	\N	Amy	Poehling	4608	4363	2025-06-24 19:48:54.082673-05	nndz-WkNHNXdMcndnZz09	4513	t	\N	0	0	0.00		2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
325589	\N	Ashley	Ziemba	4608	4363	2025-06-24 19:48:54.082673-05	nndz-WkM2eHg3ejlqUT09	4513	t	\N	0	0	0.00		2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
325590	\N	Wendy	Baker	4608	4363	2025-06-24 19:48:54.082673-05	nndz-WkNHN3dMbjdoUT09	4513	t	\N	4	8	33.30		2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
325591	\N	Susan	Gottlieb	4608	4363	2025-06-24 19:48:54.082673-05	nndz-WkM2eHhyM3doUT09	4513	t	\N	7	1	87.50		2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
325592	\N	Kathy	McCabe	4608	4363	2025-06-24 19:48:54.082673-05	nndz-WkNHNXdMcndnQT09	4513	t	\N	6	4	60.00		2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
325593	\N	Annie	Miskella	4608	4363	2025-06-24 19:48:54.082673-05	nndz-WkNDL3diajVqQT09	4513	t	\N	4	8	33.30		2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
325594	\N	Julie	Moran	4608	4363	2025-06-24 19:48:54.082673-05	nndz-WkNHNXlMLzlnZz09	4513	t	\N	6	4	60.00		2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
325595	\N	Kathy	Ryan	4608	4363	2025-06-24 19:48:54.082673-05	nndz-WkM2eHlicjlnQT09	4513	t	\N	5	10	33.30		2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
325596	\N	Jenny	Sloan	4608	4363	2025-06-24 19:48:54.082673-05	nndz-WkM2eHliNzRnQT09	4513	t	\N	5	4	55.60		2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
325597	\N	Mary	Ann Spencer	4608	4363	2025-06-24 19:48:54.082673-05	nndz-WkM2eHhyM3doZz09	4513	t	\N	7	4	63.60		2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
325598	\N	Janie	Tough	4608	4363	2025-06-24 19:48:54.082673-05	nndz-WlNlN3dMNzVnUT09	4513	t	\N	3	7	30.00		2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
325599	\N	Meredith	Sullivan	4617	4363	2025-06-24 19:48:54.082673-05	nndz-WkNDOHlMZndnUT09	4513	t	\N	5	3	62.50	C	2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
325600	\N	Lindsay	Bloom	4617	4363	2025-06-24 19:48:54.082673-05	nndz-WkNDL3diNzVodz09	4513	t	\N	7	2	77.80	CC	2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
325601	\N	Katie	Brickman	4617	4363	2025-06-24 19:48:54.082673-05	nndz-WkNDOHlMMzVqUT09	4513	t	\N	5	2	71.40		2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
325602	\N	Marion	Christoph	4617	4363	2025-06-24 19:48:54.082673-05	nndz-WkNDOHlMZndqUT09	4513	t	\N	2	6	25.00		2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
325603	\N	Ali	Gerchen	4617	4363	2025-06-24 19:48:54.082673-05	nndz-WkM2eHg3Nzdodz09	4513	t	\N	0	0	0.00		2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
325604	\N	Grace	Gescheidle	4617	4363	2025-06-24 19:48:54.082673-05	nndz-WlNlN3lidjZoQT09	4513	t	\N	6	4	60.00		2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
325605	\N	Wendy	Hubbard	4617	4363	2025-06-24 19:48:54.082673-05	nndz-WkNDOHlMaitodz09	4513	t	\N	1	5	16.70		2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
325606	\N	Sara	Hunter	4617	4363	2025-06-24 19:48:54.082673-05	nndz-WlNlN3lidjZodz09	4513	t	\N	0	1	0.00		2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
325607	\N	Elizabeth	Pruett	4617	4363	2025-06-24 19:48:54.082673-05	nndz-WkM2eHg3NzdnUT09	4513	t	\N	1	4	20.00		2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
325608	\N	Kim	Robb	4617	4363	2025-06-24 19:48:54.082673-05	nndz-WkNDOHlMZndnZz09	4513	t	\N	1	0	100.00		2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
325609	\N	Stacy	Sanderson	4617	4363	2025-06-24 19:48:54.082673-05	nndz-WkNHNXhMejhnQT09	4513	t	\N	1	6	14.30		2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
325610	\N	Catherine	Yehle	4617	4363	2025-06-24 19:48:54.082673-05	nndz-WkMrL3lMbjRoUT09	4513	t	\N	0	5	0.00		2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
325611	\N	Emily	Krall	4617	4363	2025-06-24 19:48:54.082673-05	nndz-WkM2eHg3NzdoZz09	4513	t	\N	1	0	100.00		2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
325612	\N	Claudia	Altounian	4617	4363	2025-06-24 19:48:54.082673-05	nndz-WkNDK3lMZndqUT09	4513	t	\N	0	0	0.00		2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
325613	\N	Maureen	Bennett	4617	4363	2025-06-24 19:48:54.082673-05	nndz-WkM2eHg3NzRqQT09	4513	t	\N	0	0	0.00		2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
325614	\N	Kathleen	Brill	4617	4363	2025-06-24 19:48:54.082673-05	nndz-WkM2eHg3NzdoUT09	4513	t	\N	0	0	0.00		2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
325615	\N	Jennifer	Buettner	4617	4363	2025-06-24 19:48:54.082673-05	nndz-WkNDeHdiN3dnUT09	4513	t	\N	0	0	0.00		2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
325616	\N	Sophie	Byers	4617	4363	2025-06-24 19:48:54.082673-05	nndz-WkNHNXdyYjlnUT09	4513	t	\N	0	0	0.00		2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
325617	\N	Nicole	Cooper	4617	4363	2025-06-24 19:48:54.082673-05	nndz-WkM2eHg3NzdoQT09	4513	t	\N	0	0	0.00		2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
325618	\N	Phoebe	DePree	4617	4363	2025-06-24 19:48:54.082673-05	nndz-WkNDL3diejRndz09	4513	t	\N	0	0	0.00		2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
325619	\N	Julie	Gish	4617	4363	2025-06-24 19:48:54.082673-05	nndz-WkNDeHdiNzdnUT09	4513	t	\N	0	0	0.00		2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
325620	\N	Cece	Gottman	4617	4363	2025-06-24 19:48:54.082673-05	nndz-WkMrN3hicnhnUT09	4513	t	\N	0	5	0.00		2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
325621	\N	Kate	Kelliher	4617	4363	2025-06-24 19:48:54.082673-05	nndz-WkNDL3diejRnZz09	4513	t	\N	0	0	0.00		2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
325622	\N	Courtney	McGovern	4617	4363	2025-06-24 19:48:54.082673-05	nndz-WkNHNXdyYjlnQT09	4513	t	\N	0	0	0.00		2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
325623	\N	Jennifer	Randolph	4617	4363	2025-06-24 19:48:54.082673-05	nndz-WkNHNXdyYjhoQT09	4513	t	\N	0	0	0.00		2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
325624	\N	Angie	Sandner	4617	4363	2025-06-24 19:48:54.082673-05	nndz-WkM2eHg3NzdnQT09	4513	t	\N	0	0	0.00		2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
325625	\N	Amy	Wells	4617	4363	2025-06-24 19:48:54.082673-05	nndz-WkNHNXdyYjlnZz09	4513	t	\N	0	0	0.00		2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
325626	\N	Carla	Wyckoff	4617	4363	2025-06-24 19:48:54.082673-05	nndz-WkM2d3hML3doQT09	4513	t	\N	0	0	0.00		2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
325627	\N	Janet	Maxwell-Wickett	4618	4363	2025-06-24 19:48:54.082673-05	nndz-WkM2eHhydjZnQT09	4513	t	\N	4	3	57.10	C	2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
325628	\N	Tiffany	Kraft	4618	4363	2025-06-24 19:48:54.082673-05	nndz-WkNHNXdyZjRnZz09	4513	t	\N	15	13	53.60	CC	2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
325629	\N	Aileen	O'Malley	4618	4363	2025-06-24 19:48:54.082673-05	nndz-WkNHNXdyZjRndz09	4513	t	\N	5	3	62.50		2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
325630	\N	Courtney	Veit	4618	4363	2025-06-24 19:48:54.082673-05	nndz-WkM2eHhydjVodz09	4513	t	\N	9	3	75.00		2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
325631	\N	Kim	Williams	4618	4363	2025-06-24 19:48:54.082673-05	nndz-WkNDL3diejRoUT09	4513	t	\N	2	1	66.70		2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
325632	\N	Nageen	Wilson	4618	4363	2025-06-24 19:48:54.082673-05	nndz-WkNDL3diNzdqQT09	4513	t	\N	3	2	60.00		2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
325633	\N	Holly	Zimmermann	4618	4363	2025-06-24 19:48:54.082673-05	nndz-WkNDL3diMzRoZz09	4513	t	\N	5	2	71.40		2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
325634	\N	Brandy	Oomen	4618	4363	2025-06-24 19:48:54.082673-05	nndz-WkM2eHhydjVoUT09	4513	t	\N	3	1	75.00		2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
325635	\N	Tammy	Stachorek	4618	4363	2025-06-24 19:48:54.082673-05	nndz-WkM2d3g3djdoUT09	4513	t	\N	8	4	66.70		2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
325636	\N	Mary	Aloisio	4618	4363	2025-06-24 19:48:54.082673-05	nndz-WkNDL3diditodz09	4513	t	\N	4	1	80.00		2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
325637	\N	Meghan	Buckman	4618	4363	2025-06-24 19:48:54.082673-05	nndz-WkMrK3dMbndqQT09	4513	t	\N	6	4	60.00		2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
325638	\N	Annie	Heigl	4618	4363	2025-06-24 19:48:54.082673-05	nndz-WkMrK3dMNytnUT09	4513	t	\N	8	2	80.00		2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
325639	\N	Jessica	India	4618	4363	2025-06-24 19:48:54.082673-05	nndz-WkMrK3dML3hodz09	4513	t	\N	6	3	66.70		2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
325640	\N	Gina	Johnson	4618	4363	2025-06-24 19:48:54.082673-05	nndz-WkMrK3dicitodz09	4513	t	\N	12	2	85.70		2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
325641	\N	Jill	Munce	4618	4363	2025-06-24 19:48:54.082673-05	nndz-WkM2eHhydjZndz09	4513	t	\N	4	7	36.40		2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
325642	\N	Sara	Woll	4618	4363	2025-06-24 19:48:54.082673-05	nndz-WkNHN3hMbnhoQT09	4513	t	\N	8	1	88.90		2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
325643	\N	Tracy	Winslow	4635	4363	2025-06-24 19:48:54.082673-05	nndz-WkNDL3dicjdndz09	4513	t	\N	7	6	53.80	C	2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
325644	\N	Jennifer	Tarr	4635	4363	2025-06-24 19:48:54.082673-05	nndz-WkM2eHg3ejhnUT09	4513	t	\N	4	4	50.00	CC	2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
325645	\N	Jennifer	Balestrery	4635	4363	2025-06-24 19:48:54.082673-05	nndz-WkNDL3diejlqQT09	4513	t	\N	2	3	40.00		2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
325646	\N	Andrea	Bechtel	4635	4363	2025-06-24 19:48:54.082673-05	nndz-WkNDOHlMcjVnQT09	4513	t	\N	3	2	60.00		2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
325647	\N	Melissa	Corley	4635	4363	2025-06-24 19:48:54.082673-05	nndz-WkNDL3didjhoQT09	4513	t	\N	0	0	0.00		2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
325648	\N	Julie	Hallinan	4635	4363	2025-06-24 19:48:54.082673-05	nndz-WkNDL3diNytndz09	4513	t	\N	0	1	0.00		2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
325649	\N	Catherine	Hurtgen	4635	4363	2025-06-24 19:48:54.082673-05	nndz-WkNDOHlMbitodz09	4513	t	\N	3	2	60.00		2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
325650	\N	Kim	Melancon	4635	4363	2025-06-24 19:48:54.082673-05	nndz-WkNDL3diN3hndz09	4513	t	\N	2	4	33.30		2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
325651	\N	Holly	Newcomb	4635	4363	2025-06-24 19:48:54.082673-05	nndz-WkNDL3dicnhndz09	4513	t	\N	3	8	27.30		2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
325652	\N	Kate	Osmond	4635	4363	2025-06-24 19:48:54.082673-05	nndz-WkM2eHhyajdnQT09	4513	t	\N	7	2	77.80		2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
325653	\N	Priya	Roop	4635	4363	2025-06-24 19:48:54.082673-05	nndz-WkNHNXdMdjVqUT09	4513	t	\N	4	3	57.10		2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
325654	\N	Cynthia	Werts	4635	4363	2025-06-24 19:48:54.082673-05	nndz-WkNDL3diNytnZz09	4513	t	\N	3	4	42.90		2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
325655	\N	Kristin	Kavanagh	4635	4363	2025-06-24 19:48:54.082673-05	nndz-WkM2eHhyai9oQT09	4513	t	\N	3	4	42.90		2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
325656	\N	Laura	Margolis	4635	4363	2025-06-24 19:48:54.082673-05	nndz-WkMrK3diZndodz09	4513	t	\N	6	3	66.70		2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
325657	\N	Heather	Wojteczko	4635	4363	2025-06-24 19:48:54.082673-05	nndz-WkM2d3c3bjlodz09	4513	t	\N	9	3	75.00		2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
325658	\N	Debbie	Frei	4635	4363	2025-06-24 19:48:54.082673-05	nndz-WkNHNHdiaitoZz09	4513	t	\N	3	7	30.00		2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
325659	\N	Liz	Kosky	4638	4363	2025-06-24 19:48:54.082673-05	nndz-WkNDL3diejdoQT09	4513	t	\N	5	2	71.40	C	2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
325660	\N	Mary	Lynn Sims	4638	4363	2025-06-24 19:48:54.082673-05	nndz-WkNDL3diNzhnUT09	4513	t	\N	5	2	71.40	CC	2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
325661	\N	Tara	Baker	4638	4363	2025-06-24 19:48:54.082673-05	nndz-WkM2eHg3N3doZz09	4513	t	\N	6	2	75.00		2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
325662	\N	Dani	Berman	4638	4363	2025-06-24 19:48:54.082673-05	nndz-WkM2eHg3N3dndz09	4513	t	\N	8	1	88.90		2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
325663	\N	Cindy	Brady	4638	4363	2025-06-24 19:48:54.082673-05	nndz-WkNDOHlMZjRnUT09	4513	t	\N	7	0	100.00		2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
325664	\N	Michelle	Culver	4638	4363	2025-06-24 19:48:54.082673-05	nndz-WkNDL3diNzhqQT09	4513	t	\N	5	2	71.40		2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
325665	\N	Carol	Deitch	4638	4363	2025-06-24 19:48:54.082673-05	nndz-WkNDOHlMcnhoUT09	4513	t	\N	3	3	50.00		2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
325666	\N	Susie	Lees	4638	4363	2025-06-24 19:48:54.082673-05	nndz-WkM2eHg3N3dqQT09	4513	t	\N	5	2	71.40		2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
325667	\N	Lori	Moros	4638	4363	2025-06-24 19:48:54.082673-05	nndz-WkM2eHlMejVoUT09	4513	t	\N	0	0	0.00		2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
325668	\N	Stef	Pinsky	4638	4363	2025-06-24 19:48:54.082673-05	nndz-WkM2eHg3LzVoUT09	4513	t	\N	4	3	57.10		2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
325669	\N	Jo	Ann Seager	4638	4363	2025-06-24 19:48:54.082673-05	nndz-WkM2eHlML3dnZz09	4513	t	\N	4	3	57.10		2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
325670	\N	Lisa	Crist	4638	4363	2025-06-24 19:48:54.082673-05	nndz-WkNDL3diNzhnQT09	4513	t	\N	2	3	40.00		2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
325671	\N	Jane	Sotos	4638	4363	2025-06-24 19:48:54.082673-05	nndz-WkM2eHhybnhnZz09	4513	t	\N	7	1	87.50		2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
325672	\N	Kate	Reed	4640	4363	2025-06-24 19:48:54.082673-05	nndz-WkMrL3lMbjRoZz09	4513	t	\N	1	0	100.00	C	2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
325673	\N	Anne	Hart	4640	4363	2025-06-24 19:48:54.082673-05	nndz-WkNDL3diditoZz09	4513	t	\N	4	5	44.40	CC	2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
325674	\N	Stephanie	Adam	4640	4363	2025-06-24 19:48:54.082673-05	nndz-WkM2eHhyZjhoQT09	4513	t	\N	5	3	62.50		2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
325675	\N	Betsie	Ball	4640	4363	2025-06-24 19:48:54.082673-05	nndz-WkNDL3diejZqUT09	4513	t	\N	4	2	66.70		2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
325676	\N	Tricia	Chookaszian	4640	4363	2025-06-24 19:48:54.082673-05	nndz-WkNDL3diLzdqUT09	4513	t	\N	2	3	40.00		2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
325677	\N	Karen	Fata	4640	4363	2025-06-24 19:48:54.082673-05	nndz-WkNDL3diLzRnQT09	4513	t	\N	4	1	80.00		2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
325678	\N	Kate	Schuppan	4640	4363	2025-06-24 19:48:54.082673-05	nndz-WkNHNXc3cjhqQT09	4513	t	\N	4	2	66.70		2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
325679	\N	Carrie	Diamond	4640	4363	2025-06-24 19:48:54.082673-05	nndz-WkM2eHhyZjhoZz09	4513	t	\N	3	3	50.00		2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
325680	\N	Lisa	Farrell	4640	4363	2025-06-24 19:48:54.082673-05	nndz-WkNDL3dicndoUT09	4513	t	\N	6	4	60.00		2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
325681	\N	Jenner	Schlafly	4640	4363	2025-06-24 19:48:54.082673-05	nndz-WkM2eHhyZi9oUT09	4513	t	\N	9	3	75.00		2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
325682	\N	Nicole	Doherty	4640	4363	2025-06-24 19:48:54.082673-05	nndz-WkMreHdicjhoQT09	4513	t	\N	12	4	75.00		2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
325683	\N	Adrienne	Eynon	4640	4363	2025-06-24 19:48:54.082673-05	nndz-WkM2eHhyZndodz09	4513	t	\N	13	4	76.50		2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
325684	\N	Mary	Jo Lestingi	4640	4363	2025-06-24 19:48:54.082673-05	nndz-WkM2eHg3ejZodz09	4513	t	\N	2	1	66.70		2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
325685	\N	Mary	White	4640	4363	2025-06-24 19:48:54.082673-05	nndz-WkM2eHhyZitnUT09	4513	t	\N	3	1	75.00		2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
325686	\N	Christina	Glisson	4640	4363	2025-06-24 19:48:54.082673-05	nndz-WkM2eHhyZjdnUT09	4513	t	\N	5	3	62.50		2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
325687	\N	REBECCA	WADMAN	4640	4363	2025-06-24 19:48:54.082673-05	nndz-WlNlN3hiNzRoZz09	4513	t	\N	11	1	91.70		2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
325688	\N	Daniella	Watkins	4640	4363	2025-06-24 19:48:54.082673-05	nndz-WkM2eHliNzRqUT09	4513	t	\N	4	7	36.40		2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
325689	\N	Sarah	Fuller	4646	4363	2025-06-24 19:48:54.082673-05	nndz-WkM2eHhidjlnQT09	4513	t	\N	5	3	62.50	C	2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
325690	\N	Julie	Doell	4646	4363	2025-06-24 19:48:54.082673-05	nndz-WkM2eHhidjloZz09	4513	t	\N	3	4	42.90	CC	2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
325691	\N	Diane	Goodwin	4646	4363	2025-06-24 19:48:54.082673-05	nndz-WkM2eHdycjRnUT09	4513	t	\N	3	6	33.30		2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
325692	\N	Tiffany	Laczkowski	4646	4363	2025-06-24 19:48:54.082673-05	nndz-WkNDOHlMZi9qQT09	4513	t	\N	4	5	44.40		2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
325693	\N	Debi	Loarie	4646	4363	2025-06-24 19:48:54.082673-05	nndz-WkNDL3diMzRqQT09	4513	t	\N	1	0	100.00		2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
325694	\N	Hannah	Plumpton	4646	4363	2025-06-24 19:48:54.082673-05	nndz-WkMrK3diM3hndz09	4513	t	\N	3	4	42.90		2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
325695	\N	Eileen	Rosenfeld	4646	4363	2025-06-24 19:48:54.082673-05	nndz-WkNDOHlMbi9nZz09	4513	t	\N	4	4	50.00		2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
325696	\N	Abby	Sarnoff	4646	4363	2025-06-24 19:48:54.082673-05	nndz-WkNDL3diLzhnQT09	4513	t	\N	3	6	33.30		2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
325697	\N	Cheryl	Schwartz	4646	4363	2025-06-24 19:48:54.082673-05	nndz-WkNDOHlMajlndz09	4513	t	\N	2	4	33.30		2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
325698	\N	Stacey	Wilson	4646	4363	2025-06-24 19:48:54.082673-05	nndz-WkM2d3c3ZjZqUT09	4513	t	\N	2	3	40.00		2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
325699	\N	Leslie	Weyhrich	4646	4363	2025-06-24 19:48:54.082673-05	nndz-WkNHNXdyLzhndz09	4513	t	\N	0	1	0.00		2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
325700	\N	Jackie	Rosinus	4646	4363	2025-06-24 19:48:54.082673-05	nndz-WkNHNHliZitoZz09	4513	t	\N	8	2	80.00		2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
325701	\N	Anne	Sullivan	4646	4363	2025-06-24 19:48:54.082673-05	nndz-WkM2eHhidjZnQT09	4513	t	\N	1	0	100.00		2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
325702	\N	Samantha	Weinberg	4646	4363	2025-06-24 19:48:54.082673-05	nndz-WkMrK3hiajRqQT09	4513	t	\N	8	3	72.70		2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
325703	\N	Meg	Zuehl	4646	4363	2025-06-24 19:48:54.082673-05	nndz-WkM2d3hidnhqQT09	4513	t	\N	10	6	62.50		2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
325704	\N	Erin	Vondra	4567	4331	2025-06-24 19:48:54.082673-05	nndz-WkNHNHlMcjZqUT09	4513	t	\N	6	0	100.00	C	2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
325705	\N	Lauren	Klauer	4567	4331	2025-06-24 19:48:54.082673-05	nndz-WkM2eHhidjZoQT09	4513	t	\N	3	0	100.00	CC	2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
325706	\N	Anne	Baumfeld	4567	4331	2025-06-24 19:48:54.082673-05	nndz-WkM2eHg3ZjhoQT09	4513	t	\N	0	3	0.00		2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
325707	\N	Carla	Janess	4567	4331	2025-06-24 19:48:54.082673-05	nndz-WkM2eHg3ZitnUT09	4513	t	\N	6	1	85.70		2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
325708	\N	Ali	Laumann	4567	4331	2025-06-24 19:48:54.082673-05	nndz-WkM2eHg3ZnhnQT09	4513	t	\N	4	0	100.00		2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
325709	\N	Kristin	Routhieaux	4567	4331	2025-06-24 19:48:54.082673-05	nndz-WkM2eHg3ZjhnQT09	4513	t	\N	3	1	75.00		2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
325710	\N	Kelley	Schauenberg	4567	4331	2025-06-24 19:48:54.082673-05	nndz-WkNDOHlML3hoZz09	4513	t	\N	5	2	71.40		2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
325711	\N	Rachel	Schiewe	4567	4331	2025-06-24 19:48:54.082673-05	nndz-WkM2eHg3Zjhndz09	4513	t	\N	6	1	85.70		2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
325712	\N	Christie	Shoemacher	4567	4331	2025-06-24 19:48:54.082673-05	nndz-WkM2eHg3ZjhnZz09	4513	t	\N	6	2	75.00		2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
325713	\N	Michelle	Solberg	4567	4331	2025-06-24 19:48:54.082673-05	nndz-WkM2eHg3ZjhqUT09	4513	t	\N	3	3	50.00		2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
325714	\N	Jenny	Welsh	4567	4331	2025-06-24 19:48:54.082673-05	nndz-WkM2eHg3Zi9oUT09	4513	t	\N	4	1	80.00		2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
325715	\N	Amy	Wickstrom	4567	4331	2025-06-24 19:48:54.082673-05	nndz-WkM2eHg3Zi9oQT09	4513	t	\N	0	0	0.00		2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
325716	\N	Katie	Wilson - BHCC	4567	4331	2025-06-24 19:48:54.082673-05	nndz-WkNHNHlMcjZqQT09	4513	t	\N	5	1	83.30		2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
325717	\N	Hilary	Atamian	4567	4331	2025-06-24 19:48:54.082673-05	nndz-WlNlNnlidjhndz09	4513	t	\N	1	2	33.30		2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
325718	\N	Jakie	Babel	4567	4331	2025-06-24 19:48:54.082673-05	nndz-WkMrN3hyajdoQT09	4513	t	\N	0	0	0.00		2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
325719	\N	Jodie	Barbera	4567	4331	2025-06-24 19:48:54.082673-05	nndz-WkNHNXdyLzdqQT09	4513	t	\N	0	2	0.00		2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
325720	\N	Melissa	Buckley	4567	4331	2025-06-24 19:48:54.082673-05	nndz-WkNDeHdiN3hoZz09	4513	t	\N	3	6	33.30		2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
325721	\N	Georgia	Campbell	4567	4331	2025-06-24 19:48:54.082673-05	nndz-WkNHNXdyLzdodz09	4513	t	\N	2	3	40.00		2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
325722	\N	Kelly	Johnson	4567	4331	2025-06-24 19:48:54.082673-05	nndz-WkM2eHg3ZjhnUT09	4513	t	\N	0	1	0.00		2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
325723	\N	Kim	Lee	4567	4331	2025-06-24 19:48:54.082673-05	nndz-WkMrN3hyajdoUT09	4513	t	\N	0	0	0.00		2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
325724	\N	Hillary	Lockefeer	4567	4331	2025-06-24 19:48:54.082673-05	nndz-WkNHNXdyLzdnUT09	4513	t	\N	0	0	0.00		2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
325725	\N	Lanisa	Tricoci Scurto	4567	4331	2025-06-24 19:48:54.082673-05	nndz-WkMrK3dMMzZodz09	4513	t	\N	4	3	57.10		2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
325726	\N	Billie	Diamond	4580	4331	2025-06-24 19:48:54.082673-05	nndz-WkM2eHhyLzdnZz09	4513	t	\N	9	7	56.20	C	2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
325727	\N	Lilia	Barba	4580	4331	2025-06-24 19:48:54.082673-05	nndz-WkM2eHliLy9oQT09	4513	t	\N	7	6	53.80		2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
325728	\N	Kristen	Dowd	4580	4331	2025-06-24 19:48:54.082673-05	nndz-WkNDL3dibnhodz09	4513	t	\N	4	3	57.10		2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
325729	\N	Liz	Jacob	4580	4331	2025-06-24 19:48:54.082673-05	nndz-WkNDeHdiLzdnUT09	4513	t	\N	0	0	0.00		2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
325730	\N	Jennifer	Mallamud	4580	4331	2025-06-24 19:48:54.082673-05	nndz-WkM2eHhyLzdoQT09	4513	t	\N	7	1	87.50		2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
325731	\N	Kate	Marciano	4580	4331	2025-06-24 19:48:54.082673-05	nndz-WkNDL3diei9oZz09	4513	t	\N	5	2	71.40		2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
325732	\N	Katie	Murlas	4580	4331	2025-06-24 19:48:54.082673-05	nndz-WkM2eHhyLzdoZz09	4513	t	\N	5	2	71.40		2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
325733	\N	Maggie	Topalian	4580	4331	2025-06-24 19:48:54.082673-05	nndz-WkM2eHhyei9nZz09	4513	t	\N	3	2	60.00		2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
325734	\N	Lisa	Clagg	4580	4331	2025-06-24 19:48:54.082673-05	nndz-WkM2eHhyLzRqQT09	4513	t	\N	10	3	76.90		2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
325735	\N	Jenny	Zecevich	4580	4331	2025-06-24 19:48:54.082673-05	nndz-WkM2eHhyLzloQT09	4513	t	\N	8	6	57.10		2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
325736	\N	Laurian	Greenbury	4580	4331	2025-06-24 19:48:54.082673-05	nndz-WkNDL3dici9nUT09	4513	t	\N	0	0	0.00		2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
325737	\N	Maureen	Griffith	4580	4331	2025-06-24 19:48:54.082673-05	nndz-WkNDL3diL3hoUT09	4513	t	\N	0	0	0.00		2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
325738	\N	Pam	Soper	4580	4331	2025-06-24 19:48:54.082673-05	nndz-WkM2eHhyLzdnUT09	4513	t	\N	4	2	66.70		2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
325739	\N	Robin	Ekenberg	4580	4331	2025-06-24 19:48:54.082673-05	nndz-WkNDL3dicitoUT09	4513	t	\N	1	8	11.10		2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
325740	\N	Erin	Lawler	4580	4331	2025-06-24 19:48:54.082673-05	nndz-WkM2eHhyLzlqQT09	4513	t	\N	6	2	75.00		2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
325741	\N	Leah	Mayer	4580	4331	2025-06-24 19:48:54.082673-05	nndz-WkM2eHhyLzZoZz09	4513	t	\N	3	5	37.50		2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
325742	\N	Maro	Zrike	4580	4331	2025-06-24 19:48:54.082673-05	nndz-WkM2eHhyLy9oZz09	4513	t	\N	6	3	66.70		2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
325743	\N	Heidi	Clifton	4595	4331	2025-06-24 19:48:54.082673-05	nndz-WkNDOHlMZjVoQT09	4513	t	\N	6	4	60.00	C	2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
325744	\N	Maggie	Wehmer	4595	4331	2025-06-24 19:48:54.082673-05	nndz-WkNHNXdMcjVoZz09	4513	t	\N	1	4	20.00	CC	2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
325745	\N	Marjorie	Alutto	4595	4331	2025-06-24 19:48:54.082673-05	nndz-WkM2eHg3ejdodz09	4513	t	\N	0	0	0.00		2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
325746	\N	Lisette	Dailey	4595	4331	2025-06-24 19:48:54.082673-05	nndz-WkNDL3diejhqUT09	4513	t	\N	4	1	80.00		2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
325747	\N	Chrissy	Davis	4595	4331	2025-06-24 19:48:54.082673-05	nndz-WkNDK3lMZndnQT09	4513	t	\N	2	3	40.00		2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
325748	\N	Sue	Kutschke	4595	4331	2025-06-24 19:48:54.082673-05	nndz-WlNlNng3ZjdoUT09	4513	t	\N	0	1	0.00		2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
325749	\N	Catherine	Lamb	4595	4331	2025-06-24 19:48:54.082673-05	nndz-WkNDL3dicjloQT09	4513	t	\N	3	3	50.00		2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
325750	\N	Kristen	Minsky	4595	4331	2025-06-24 19:48:54.082673-05	nndz-WkMrK3hiejdnUT09	4513	t	\N	5	4	55.60		2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
325751	\N	Sue	Slaughter	4595	4331	2025-06-24 19:48:54.082673-05	nndz-WkNDOHlMZjVnQT09	4513	t	\N	0	1	0.00		2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
325752	\N	Lindsey	White	4595	4331	2025-06-24 19:48:54.082673-05	nndz-WkM2eHg3ejdnUT09	4513	t	\N	0	1	0.00		2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
325753	\N	Julie	Carter	4595	4331	2025-06-24 19:48:54.082673-05	nndz-WkNHNXdMM3hndz09	4513	t	\N	4	3	57.10		2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
325754	\N	Kristen	Esplin	4595	4331	2025-06-24 19:48:54.082673-05	nndz-WkNDL3dicjZqUT09	4513	t	\N	3	5	37.50		2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
325755	\N	Susan	McMahon	4595	4331	2025-06-24 19:48:54.082673-05	nndz-WkNHNXdMcjVoQT09	4513	t	\N	4	5	44.40		2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
325756	\N	Erin	Bearman	4595	4331	2025-06-24 19:48:54.082673-05	nndz-WkM2eHhyejlnZz09	4513	t	\N	9	3	75.00		2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
325757	\N	Blair	Littel	4595	4331	2025-06-24 19:48:54.082673-05	nndz-WkM2eHhyejhoZz09	4513	t	\N	6	1	85.70		2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
325758	\N	Kirsten	Starr	4599	4331	2025-06-24 19:48:54.082673-05	nndz-WkNDL3dicjVodz09	4513	t	\N	7	2	77.80	C	2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
325759	\N	Grace	Beth Stutzmann	4599	4331	2025-06-24 19:48:54.082673-05	nndz-WkNDL3didjRqQT09	4513	t	\N	4	1	80.00	CC	2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
325760	\N	Michelle	Atwater	4599	4331	2025-06-24 19:48:54.082673-05	nndz-WlNlN3hiajhndz09	4513	t	\N	0	0	0.00		2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
325761	\N	Maribeth	Corbett	4599	4331	2025-06-24 19:48:54.082673-05	nndz-WkM2eHhyei9oQT09	4513	t	\N	7	1	87.50		2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
325762	\N	Lisa	Goldfayn	4599	4331	2025-06-24 19:48:54.082673-05	nndz-WkNDL3dicjVoZz09	4513	t	\N	1	4	20.00		2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
325763	\N	Shelley	Ireland	4599	4331	2025-06-24 19:48:54.082673-05	nndz-WkMrK3hiNzlqUT09	4513	t	\N	8	1	88.90		2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
325764	\N	Vanessa	Nowlin	4599	4331	2025-06-24 19:48:54.082673-05	nndz-WkM2eHhyei9nUT09	4513	t	\N	8	2	80.00		2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
325765	\N	Shirley	Serbin	4599	4331	2025-06-24 19:48:54.082673-05	nndz-WkNDL3diejRqUT09	4513	t	\N	2	4	33.30		2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
325766	\N	Carrie	Steinbach	4599	4331	2025-06-24 19:48:54.082673-05	nndz-WkM2eHhyei9nQT09	4513	t	\N	8	3	72.70		2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
325767	\N	Niki	Walsh	4599	4331	2025-06-24 19:48:54.082673-05	nndz-WkMrNnc3di9oZz09	4513	t	\N	2	3	40.00		2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
325768	\N	Anna	Dau	4599	4331	2025-06-24 19:48:54.082673-05	nndz-WkM2eHhyeitnZz09	4513	t	\N	6	2	75.00		2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
325769	\N	Amy	Kress Taylor	4599	4331	2025-06-24 19:48:54.082673-05	nndz-WkM2eHhyeitodz09	4513	t	\N	4	4	50.00		2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
325770	\N	Tara	Marazita	4599	4331	2025-06-24 19:48:54.082673-05	nndz-WkMrL3lMejhnQT09	4513	t	\N	5	4	55.60		2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
325771	\N	Erica	Scully	4608	4331	2025-06-24 19:48:54.082673-05	nndz-WkNDL3diM3hndz09	4513	t	\N	2	4	33.30	C	2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
325772	\N	Jen	Truszkowski	4608	4331	2025-06-24 19:48:54.082673-05	nndz-WkNDL3diMytodz09	4513	t	\N	1	7	12.50	CC	2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
325773	\N	Mandy	Breaker	4608	4331	2025-06-24 19:48:54.082673-05	nndz-WkM2eHhyM3hqQT09	4513	t	\N	2	8	20.00		2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
325774	\N	Amy	Devore	4608	4331	2025-06-24 19:48:54.082673-05	nndz-WkNHNHlMenhnQT09	4513	t	\N	5	6	45.50		2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
325775	\N	Shannon	Page	4608	4331	2025-06-24 19:48:54.082673-05	nndz-WkM2eHhyM3doQT09	4513	t	\N	3	3	50.00		2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
325776	\N	Liz	Van Horn	4608	4331	2025-06-24 19:48:54.082673-05	nndz-WlNlNHhMdjZnQT09	4513	t	\N	2	3	40.00		2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
325777	\N	Wendy	Baker	4608	4331	2025-06-24 19:48:54.082673-05	nndz-WkNHN3dMbjdoUT09	4513	t	\N	4	8	33.30		2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
325778	\N	Annie	Miskella	4608	4331	2025-06-24 19:48:54.082673-05	nndz-WkNDL3diajVqQT09	4513	t	\N	4	8	33.30		2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
325779	\N	Jenny	Sloan	4608	4331	2025-06-24 19:48:54.082673-05	nndz-WkM2eHliNzRnQT09	4513	t	\N	5	4	55.60		2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
325780	\N	Mary	Ann Spencer	4608	4331	2025-06-24 19:48:54.082673-05	nndz-WkM2eHhyM3doZz09	4513	t	\N	7	4	63.60		2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
325781	\N	Janie	Tough	4608	4331	2025-06-24 19:48:54.082673-05	nndz-WlNlN3dMNzVnUT09	4513	t	\N	3	7	30.00		2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
325782	\N	Kathy	Ryan	4608	4331	2025-06-24 19:48:54.082673-05	nndz-WkM2eHlicjlnQT09	4513	t	\N	5	10	33.30		2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
325783	\N	Nora	Andrews	4611	4331	2025-06-24 19:48:54.082673-05	nndz-WkNDL3dicjRodz09	4513	t	\N	0	1	0.00	C	2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
325784	\N	Mandy	Chiarieri	4611	4331	2025-06-24 19:48:54.082673-05	nndz-WkNDOHlMYnhnZz09	4513	t	\N	2	5	28.60	CC	2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
325785	\N	Lindsay	Doyle	4611	4331	2025-06-24 19:48:54.082673-05	nndz-WkNDL3dicjVqUT09	4513	t	\N	2	6	25.00		2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
325786	\N	Becca	Goering	4611	4331	2025-06-24 19:48:54.082673-05	nndz-WkNDL3dicjRndz09	4513	t	\N	4	3	57.10		2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
325787	\N	Bethany	Guerin	4611	4331	2025-06-24 19:48:54.082673-05	nndz-WkM2eHg3aitnQT09	4513	t	\N	2	4	33.30		2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
325788	\N	Eileen	Kasten	4611	4331	2025-06-24 19:48:54.082673-05	nndz-WkNDOHlMcjVoQT09	4513	t	\N	3	4	42.90		2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
325789	\N	Liz	Lapp	4611	4331	2025-06-24 19:48:54.082673-05	nndz-WkM2eHg3ai9oUT09	4513	t	\N	4	5	44.40		2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
325790	\N	Suzanne	O'Brien	4611	4331	2025-06-24 19:48:54.082673-05	nndz-WkNDOHlMYndodz09	4513	t	\N	2	5	28.60		2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
325791	\N	Maura	Oliver	4611	4331	2025-06-24 19:48:54.082673-05	nndz-WkNDL3diM3dnUT09	4513	t	\N	2	5	28.60		2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
325792	\N	Jennifer	Walsh - NSCC	4611	4331	2025-06-24 19:48:54.082673-05	nndz-WkNDL3didjZqQT09	4513	t	\N	4	7	36.40		2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
325793	\N	Cynthia	Avery	4611	4331	2025-06-24 19:48:54.082673-05	nndz-WkMrL3lMMzRoUT09	4513	t	\N	7	4	63.60		2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
325794	\N	Denise	Keenan	4611	4331	2025-06-24 19:48:54.082673-05	nndz-WkNHNXdMdndndz09	4513	t	\N	1	0	100.00		2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
325795	\N	Caroline	Mansour	4611	4331	2025-06-24 19:48:54.082673-05	nndz-WkNDL3diMzVqUT09	4513	t	\N	0	1	0.00		2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
325796	\N	Colleen	Shean	4611	4331	2025-06-24 19:48:54.082673-05	nndz-WkNDL3dienhnUT09	4513	t	\N	0	1	0.00		2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
325797	\N	Megan	Anderson	4611	4331	2025-06-24 19:48:54.082673-05	nndz-WkNDL3didjZnUT09	4513	t	\N	0	10	0.00		2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
325798	\N	Kirsten	Kenny	4611	4331	2025-06-24 19:48:54.082673-05	nndz-WkNDL3dicjVnQT09	4513	t	\N	1	8	11.10		2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
325799	\N	Harmony	Harrington	4618	4331	2025-06-24 19:48:54.082673-05	nndz-WkM2eHhycndnZz09	4513	t	\N	1	6	14.30	C	2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
325800	\N	Erika	Brachowski	4618	4331	2025-06-24 19:48:54.082673-05	nndz-WkNHN3dMajhndz09	4513	t	\N	2	10	16.70	CC	2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
325801	\N	Elke	Elliott	4618	4331	2025-06-24 19:48:54.082673-05	nndz-WkNDL3diNzRqQT09	4513	t	\N	0	3	0.00		2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
325802	\N	Amanda	Hill	4618	4331	2025-06-24 19:48:54.082673-05	nndz-WkM2eHhydjVqQT09	4513	t	\N	2	3	40.00		2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
325803	\N	Monika	Passannante	4618	4331	2025-06-24 19:48:54.082673-05	nndz-WkNHNXdyNytoUT09	4513	t	\N	1	7	12.50		2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
325804	\N	Kari	Rutkowski	4618	4331	2025-06-24 19:48:54.082673-05	nndz-WkNDL3diNzdnQT09	4513	t	\N	2	4	33.30		2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
325805	\N	Arrika	Kris Schneider	4618	4331	2025-06-24 19:48:54.082673-05	nndz-WkM2eHhydjRoZz09	4513	t	\N	4	8	33.30		2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
325806	\N	Heather	Sullivan	4618	4331	2025-06-24 19:48:54.082673-05	nndz-WkMrK3dMNzZoUT09	4513	t	\N	1	7	12.50		2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
325807	\N	Susan	Zimmerman	4618	4331	2025-06-24 19:48:54.082673-05	nndz-WkNHNXdyNytnQT09	4513	t	\N	1	8	11.10		2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
325808	\N	Sara	Woll	4618	4331	2025-06-24 19:48:54.082673-05	nndz-WkNHN3hMbnhoQT09	4513	t	\N	8	1	88.90		2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
325809	\N	Tania	Forte	4618	4331	2025-06-24 19:48:54.082673-05	nndz-WkNHNXdyNy9nUT09	4513	t	\N	4	4	50.00		2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
325810	\N	Jessica	India	4618	4331	2025-06-24 19:48:54.082673-05	nndz-WkMrK3dML3hodz09	4513	t	\N	6	3	66.70		2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
325811	\N	Gina	Johnson	4618	4331	2025-06-24 19:48:54.082673-05	nndz-WkMrK3dicitodz09	4513	t	\N	12	2	85.70		2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
325812	\N	Jill	Munce	4618	4331	2025-06-24 19:48:54.082673-05	nndz-WkM2eHhydjZndz09	4513	t	\N	4	7	36.40		2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
325813	\N	Kim	Wambach	4618	4331	2025-06-24 19:48:54.082673-05	nndz-WkM2eHhydjZqQT09	4513	t	\N	5	3	62.50		2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
325814	\N	Marissa	DiFranco	4618	4331	2025-06-24 19:48:54.082673-05	nndz-WkMrL3lMLzlnUT09	4513	t	\N	6	11	35.30		2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
325815	\N	Annie	Heigl	4618	4331	2025-06-24 19:48:54.082673-05	nndz-WkMrK3dMNytnUT09	4513	t	\N	8	2	80.00		2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
325816	\N	Erika	Phenner	4637	4331	2025-06-24 19:48:54.082673-05	nndz-WkM2eHg3bjZndz09	4513	t	\N	6	2	75.00	C	2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
325817	\N	Amy	Dimberio	4637	4331	2025-06-24 19:48:54.082673-05	nndz-WkM2eHg3bjlnZz09	4513	t	\N	4	2	66.70	CC	2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
325818	\N	Julie	Anastos	4637	4331	2025-06-24 19:48:54.082673-05	nndz-WkM2d3hMNzloQT09	4513	t	\N	0	6	0.00		2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
325819	\N	Katie	Anetsberger	4637	4331	2025-06-24 19:48:54.082673-05	nndz-WkM2eHhyanhndz09	4513	t	\N	3	2	60.00		2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
325820	\N	Emmy	Fogarty	4637	4331	2025-06-24 19:48:54.082673-05	nndz-WkM2eHg3bjdqQT09	4513	t	\N	4	3	57.10		2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
325821	\N	Julie	Loeber	4637	4331	2025-06-24 19:48:54.082673-05	nndz-WkNDL3diejRqQT09	4513	t	\N	2	5	28.60		2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
325822	\N	Ramie	Robbins	4637	4331	2025-06-24 19:48:54.082673-05	nndz-WkMrNnc3djlnZz09	4513	t	\N	1	4	20.00		2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
325823	\N	Kelly	Hondru	4637	4331	2025-06-24 19:48:54.082673-05	nndz-WkM2eHg3bjZoUT09	4513	t	\N	7	3	70.00		2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
325824	\N	Jacki	Ruh	4637	4331	2025-06-24 19:48:54.082673-05	nndz-WkNDL3didnhqUT09	4513	t	\N	5	1	83.30		2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
325825	\N	Judy	Yoo	4637	4331	2025-06-24 19:48:54.082673-05	nndz-WkM2eHg3bjZqQT09	4513	t	\N	11	5	68.80		2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
325826	\N	Abbey	Driscoll	4637	4331	2025-06-24 19:48:54.082673-05	nndz-WlNlN3c3ejlnZz09	4513	t	\N	7	1	87.50		2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
325827	\N	Jayme	Marino	4637	4331	2025-06-24 19:48:54.082673-05	nndz-WkM2eHhybjRoZz09	4513	t	\N	11	4	73.30		2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
325828	\N	Heather	Mcdevitt	4637	4331	2025-06-24 19:48:54.082673-05	nndz-WkM2eHhybjRnUT09	4513	t	\N	11	2	84.60		2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
325829	\N	Elizabeth	Silvia	4637	4331	2025-06-24 19:48:54.082673-05	nndz-WkMrK3dibjZoZz09	4513	t	\N	8	7	53.30		2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
325830	\N	Jennifer	Tucker	4637	4331	2025-06-24 19:48:54.082673-05	nndz-WkM2eHg3bjZqUT09	4513	t	\N	12	2	85.70		2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
325831	\N	Paige	Wenk	4637	4331	2025-06-24 19:48:54.082673-05	nndz-WkNDeHdiNzRoUT09	4513	t	\N	1	2	33.30		2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
325832	\N	Linda	Franke	4638	4331	2025-06-24 19:48:54.082673-05	nndz-WkNDL3diNzhqUT09	4513	t	\N	2	6	25.00	C	2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
325833	\N	Lynn	Johnstone	4638	4331	2025-06-24 19:48:54.082673-05	nndz-WkNDL3diNzhoQT09	4513	t	\N	1	3	25.00	CC	2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
325834	\N	Dayle	Berke	4638	4331	2025-06-24 19:48:54.082673-05	nndz-WkM2eHg3ejZoQT09	4513	t	\N	1	5	16.70		2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
325835	\N	Jackie	Borchew	4638	4331	2025-06-24 19:48:54.082673-05	nndz-WkNDL3diNzlnZz09	4513	t	\N	1	7	12.50		2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
325836	\N	Amy	Carletti	4638	4331	2025-06-24 19:48:54.082673-05	nndz-WkM2eHhybjdnUT09	4513	t	\N	1	7	12.50		2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
325837	\N	Caroline	Gray	4638	4331	2025-06-24 19:48:54.082673-05	nndz-WkM2eHhybnhoUT09	4513	t	\N	2	6	25.00		2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
325838	\N	Joan	LaPiana	4638	4331	2025-06-24 19:48:54.082673-05	nndz-WkNDOHlMcnhnUT09	4513	t	\N	3	2	60.00		2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
325839	\N	Peggy	Milligan	4638	4331	2025-06-24 19:48:54.082673-05	nndz-WkNDOHlMbjVoUT09	4513	t	\N	3	3	50.00		2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
325840	\N	Allison	Richman	4638	4331	2025-06-24 19:48:54.082673-05	nndz-WkM2eHhybjhndz09	4513	t	\N	1	5	16.70		2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
325841	\N	Lisa	Speed	4638	4331	2025-06-24 19:48:54.082673-05	nndz-WkM2eHhybjdqQT09	4513	t	\N	3	4	42.90		2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
325842	\N	Lisa	Crist	4638	4331	2025-06-24 19:48:54.082673-05	nndz-WkNDL3diNzhnQT09	4513	t	\N	2	3	40.00		2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
325843	\N	Jackie	Earley	4638	4331	2025-06-24 19:48:54.082673-05	nndz-WkM2eHhydnhnUT09	4513	t	\N	4	3	57.10		2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
325844	\N	Jane	Sotos	4638	4331	2025-06-24 19:48:54.082673-05	nndz-WkM2eHhybnhnZz09	4513	t	\N	7	1	87.50		2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
325845	\N	Lindsey	Lieberman	4638	4331	2025-06-24 19:48:54.082673-05	nndz-WkMrK3dMNzdnQT09	4513	t	\N	1	6	14.30		2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
325846	\N	Angie	Taggart	4642	4331	2025-06-24 19:48:54.082673-05	nndz-WkM2eHliNzVqQT09	4513	t	\N	12	3	80.00	C	2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
325847	\N	Anne	Kelly	4642	4331	2025-06-24 19:48:54.082673-05	nndz-WkNDL3didndoZz09	4513	t	\N	6	1	85.70	CC	2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
325848	\N	Diane	Graf	4642	4331	2025-06-24 19:48:54.082673-05	nndz-WkM2eHg3LzlnZz09	4513	t	\N	3	3	50.00		2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
325849	\N	Kelly	Gruner	4642	4331	2025-06-24 19:48:54.082673-05	nndz-WkMrK3g3Yjlodz09	4513	t	\N	5	2	71.40		2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
325850	\N	Amy	Hodgman	4642	4331	2025-06-24 19:48:54.082673-05	nndz-WkMrK3hiaitoQT09	4513	t	\N	6	4	60.00		2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
325851	\N	Sacha	Krasney	4642	4331	2025-06-24 19:48:54.082673-05	nndz-WkM2eHliNzRodz09	4513	t	\N	4	3	57.10		2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
325852	\N	Liz	Wesemann	4642	4331	2025-06-24 19:48:54.082673-05	nndz-WkMrN3g3ajZnZz09	4513	t	\N	5	5	50.00		2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
325853	\N	Melissa	Koss	4642	4331	2025-06-24 19:48:54.082673-05	nndz-WkMrK3hiZjdqQT09	4513	t	\N	19	5	79.20		2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
325854	\N	Maria	Parmentier	4642	4331	2025-06-24 19:48:54.082673-05	nndz-WkM2eHliNzhnUT09	4513	t	\N	10	7	58.80		2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
325855	\N	Maggie	Burke	4642	4331	2025-06-24 19:48:54.082673-05	nndz-WkMreHdMLzVqQT09	4513	t	\N	13	1	92.90		2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
325856	\N	Lisa	Goldman	4642	4331	2025-06-24 19:48:54.082673-05	nndz-WkMrN3hiM3dndz09	4513	t	\N	7	2	77.80		2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
325857	\N	Courtney	Spalding	4642	4331	2025-06-24 19:48:54.082673-05	nndz-WlNlNHlMandnZz09	4513	t	\N	7	2	77.80		2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
325858	\N	Beth	Wechsler	4642	4331	2025-06-24 19:48:54.082673-05	nndz-WkMreHdiZjhnUT09	4513	t	\N	7	2	77.80		2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
325859	\N	Emily	Williams	4642	4331	2025-06-24 19:48:54.082673-05	nndz-WlNlNng3bitnUT09	4513	t	\N	5	4	55.60		2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
325860	\N	Sondra	Raider	4567	4332	2025-06-24 19:48:54.082673-05	nndz-WkNDL3diLzlodz09	4513	t	\N	2	5	28.60	C	2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
325861	\N	Georgia	Campbell	4567	4332	2025-06-24 19:48:54.082673-05	nndz-WkNHNXdyLzdodz09	4513	t	\N	2	3	40.00		2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
325862	\N	Jean	Maddrell	4567	4332	2025-06-24 19:48:54.082673-05	nndz-WkNDL3diMzRodz09	4513	t	\N	2	5	28.60		2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
325863	\N	Colleen	Mallon	4567	4332	2025-06-24 19:48:54.082673-05	nndz-WkNDL3diLzZqUT09	4513	t	\N	4	3	57.10		2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
325864	\N	Priscilla	Mcintosh	4567	4332	2025-06-24 19:48:54.082673-05	nndz-WkNDL3diLzlndz09	4513	t	\N	0	6	0.00		2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
325865	\N	Kate	Mitten	4567	4332	2025-06-24 19:48:54.082673-05	nndz-WkNDL3diLzloQT09	4513	t	\N	2	5	28.60		2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
325866	\N	Cara	O'Hara	4567	4332	2025-06-24 19:48:54.082673-05	nndz-WkNHNXdyLzdnQT09	4513	t	\N	2	4	33.30		2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
325867	\N	Lea	Regan	4567	4332	2025-06-24 19:48:54.082673-05	nndz-WkNDL3diLzlnQT09	4513	t	\N	0	0	0.00		2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
325868	\N	Jan	Romenesko	4567	4332	2025-06-24 19:48:54.082673-05	nndz-WkNDL3diLzZnZz09	4513	t	\N	0	0	0.00		2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
325869	\N	Patti	Stickney	4567	4332	2025-06-24 19:48:54.082673-05	nndz-WkNDL3diLzhoUT09	4513	t	\N	2	6	25.00		2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
325870	\N	Sharon	Bernardo	4567	4332	2025-06-24 19:48:54.082673-05	nndz-WkNDK3lMZndodz09	4513	t	\N	0	0	0.00		2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
325871	\N	Jane	Buchel	4567	4332	2025-06-24 19:48:54.082673-05	nndz-WkNHNXdyLzdoZz09	4513	t	\N	3	6	33.30		2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
325872	\N	Melissa	Buckley	4567	4332	2025-06-24 19:48:54.082673-05	nndz-WkNDeHdiN3hoZz09	4513	t	\N	3	6	33.30		2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
325873	\N	Lynda	Coffman	4567	4332	2025-06-24 19:48:54.082673-05	nndz-WkNHNXdyLzdoQT09	4513	t	\N	1	2	33.30		2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
325874	\N	Laura	Fitch	4567	4332	2025-06-24 19:48:54.082673-05	nndz-WkM2eHg3Zi9ndz09	4513	t	\N	0	5	0.00		2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
325875	\N	Gayle	Gianopulos	4567	4332	2025-06-24 19:48:54.082673-05	nndz-WkNHNXdyLzdnZz09	4513	t	\N	1	3	25.00		2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
325876	\N	Tracy	Karambelas	4567	4332	2025-06-24 19:48:54.082673-05	nndz-WkMrK3dyZitoQT09	4513	t	\N	0	4	0.00		2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
325877	\N	Hillary	Lockefeer	4567	4332	2025-06-24 19:48:54.082673-05	nndz-WkNHNXdyLzdnUT09	4513	t	\N	0	0	0.00		2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
325878	\N	Tiffany	Marshall	4567	4332	2025-06-24 19:48:54.082673-05	nndz-WkM2eHg3Zi9qUT09	4513	t	\N	2	4	33.30		2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
325879	\N	Ashlie	McDonnell	4567	4332	2025-06-24 19:48:54.082673-05	nndz-WkMrN3lidjdnQT09	4513	t	\N	5	1	83.30		2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
325880	\N	Susan	Nelsen	4567	4332	2025-06-24 19:48:54.082673-05	nndz-WkNDeHdiNytqUT09	4513	t	\N	0	6	0.00		2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
325881	\N	Rachel	Schiewe	4567	4332	2025-06-24 19:48:54.082673-05	nndz-WkM2eHg3Zjhndz09	4513	t	\N	6	1	85.70		2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
325882	\N	Lanisa	Tricoci Scurto	4567	4332	2025-06-24 19:48:54.082673-05	nndz-WkMrK3dMMzZodz09	4513	t	\N	4	3	57.10		2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
325883	\N	Judy	West	4567	4332	2025-06-24 19:48:54.082673-05	nndz-WkNDOHlMLytqUT09	4513	t	\N	0	0	0.00		2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
325884	\N	Lindsay	Stein Cohen	4571	4332	2025-06-24 19:48:54.082673-05	nndz-WkM2eHhyNzVqUT09	4513	t	\N	5	2	71.40	C	2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
325885	\N	Lisa	Strasman	4571	4332	2025-06-24 19:48:54.082673-05	nndz-WkM2eHg3aitoUT09	4513	t	\N	8	2	80.00	CC	2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
325886	\N	Melissa	Block	4571	4332	2025-06-24 19:48:54.082673-05	nndz-WkM2eHg3aitoQT09	4513	t	\N	8	3	72.70		2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
325887	\N	Brooke	Doppelt	4571	4332	2025-06-24 19:48:54.082673-05	nndz-WkMrK3hMMytoZz09	4513	t	\N	0	0	0.00		2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
325888	\N	Stephanie	Fick	4571	4332	2025-06-24 19:48:54.082673-05	nndz-WkNHNXdyejloQT09	4513	t	\N	7	4	63.60		2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
325889	\N	Jennifer	Fisher	4571	4332	2025-06-24 19:48:54.082673-05	nndz-WkNHNXdyejlqUT09	4513	t	\N	6	5	54.50		2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
325890	\N	Lisa	Kaplan	4571	4332	2025-06-24 19:48:54.082673-05	nndz-WkNHNXdyejdoZz09	4513	t	\N	5	2	71.40		2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
325891	\N	Stephanie	Luger	4571	4332	2025-06-24 19:48:54.082673-05	nndz-WkM2eHhyNzVnQT09	4513	t	\N	6	2	75.00		2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
325892	\N	Vicki	Morton	4571	4332	2025-06-24 19:48:54.082673-05	nndz-WkNDK3lMZnhoQT09	4513	t	\N	3	3	50.00		2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
325893	\N	Jorie	Sigesmund	4571	4332	2025-06-24 19:48:54.082673-05	nndz-WkNHNXdyejZoQT09	4513	t	\N	6	2	75.00		2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
325894	\N	Marny	Kravenas	4571	4332	2025-06-24 19:48:54.082673-05	nndz-WkM2eHg3anhndz09	4513	t	\N	6	4	60.00		2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
325895	\N	Allison	Rabin	4571	4332	2025-06-24 19:48:54.082673-05	nndz-WkNHNXdyejVnQT09	4513	t	\N	4	2	66.70		2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
325896	\N	Heidi	Sachs	4571	4332	2025-06-24 19:48:54.082673-05	nndz-WkM2eHhyNzRndz09	4513	t	\N	7	4	63.60		2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
325897	\N	Jenny	Piermont	4572	4332	2025-06-24 19:48:54.082673-05	nndz-WkM2eHlicjZnQT09	4513	t	\N	10	1	90.90	C	2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
325898	\N	Elissa	Delman	4572	4332	2025-06-24 19:48:54.082673-05	nndz-WkNDL3diL3hndz09	4513	t	\N	5	3	62.50	CC	2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
325899	\N	Susan	Ballis	4572	4332	2025-06-24 19:48:54.082673-05	nndz-WkNDL3dicjVndz09	4513	t	\N	2	1	66.70		2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
325900	\N	Elizabeth	Birnbaum	4572	4332	2025-06-24 19:48:54.082673-05	nndz-WkM2eHlicjdqUT09	4513	t	\N	7	2	77.80		2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
325901	\N	Wendy	Goldman	4572	4332	2025-06-24 19:48:54.082673-05	nndz-WkM2eHg3ejdoQT09	4513	t	\N	4	3	57.10		2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
325902	\N	Alisa	Harmon	4572	4332	2025-06-24 19:48:54.082673-05	nndz-WlNhK3dMajRoUT09	4513	t	\N	1	0	100.00		2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
325903	\N	Elaine	Jacoby	4572	4332	2025-06-24 19:48:54.082673-05	nndz-WkNDOHlMZi9odz09	4513	t	\N	3	2	60.00		2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
325904	\N	Jen	Kaplan	4572	4332	2025-06-24 19:48:54.082673-05	nndz-WkNDL3didjVoQT09	4513	t	\N	4	4	50.00		2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
325905	\N	Whitney	Weiner	4572	4332	2025-06-24 19:48:54.082673-05	nndz-WlNlN3hiYjVoZz09	4513	t	\N	8	2	80.00		2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
325906	\N	Wendy	Apple	4572	4332	2025-06-24 19:48:54.082673-05	nndz-WkNHNXdyanhoZz09	4513	t	\N	8	1	88.90		2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
325907	\N	Lisa	Lord Aronson	4572	4332	2025-06-24 19:48:54.082673-05	nndz-WlNlOXhidjRndz09	4513	t	\N	2	3	40.00		2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
325908	\N	Kim	Colwyn	4572	4332	2025-06-24 19:48:54.082673-05	nndz-WkNHNXc3Yi9odz09	4513	t	\N	8	0	100.00		2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
325909	\N	Laura	Copilevitz	4572	4332	2025-06-24 19:48:54.082673-05	nndz-WkM2eHlicjdqQT09	4513	t	\N	7	4	63.60		2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
325910	\N	Courtney	Farrell	4572	4332	2025-06-24 19:48:54.082673-05	nndz-WkMrK3lMLytoUT09	4513	t	\N	5	4	55.60		2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
325911	\N	Julie	Lehrman	4572	4332	2025-06-24 19:48:54.082673-05	nndz-WkNDL3dicjRnUT09	4513	t	\N	1	5	16.70		2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
325912	\N	Susie	Morris	4572	4332	2025-06-24 19:48:54.082673-05	nndz-WkM2eHlicjZoZz09	4513	t	\N	1	0	100.00		2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
325913	\N	Carolyn	Spero	4572	4332	2025-06-24 19:48:54.082673-05	nndz-WkM2eHg3ajhnQT09	4513	t	\N	2	6	25.00		2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
325914	\N	Jodi	Taub	4572	4332	2025-06-24 19:48:54.082673-05	nndz-WkNDL3dicjRqQT09	4513	t	\N	3	2	60.00		2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
325915	\N	Elaine	Rucker	4579	4332	2025-06-24 19:48:54.082673-05	nndz-WkNHNXc3M3hoZz09	4513	t	\N	2	3	40.00	C	2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
325916	\N	Stephanie	Muno	4579	4332	2025-06-24 19:48:54.082673-05	nndz-WkM2eHhyNzlqQT09	4513	t	\N	5	3	62.50	CC	2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
325917	\N	Paula	Bork	4579	4332	2025-06-24 19:48:54.082673-05	nndz-WkNDL3didjVqQT09	4513	t	\N	0	2	0.00		2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
325918	\N	Betsy	Brace-Blum	4579	4332	2025-06-24 19:48:54.082673-05	nndz-WkM2eHhyNzloZz09	4513	t	\N	2	3	40.00		2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
325919	\N	Lauren	Edmonds	4579	4332	2025-06-24 19:48:54.082673-05	nndz-WkM2eHg3LzRoQT09	4513	t	\N	5	1	83.30		2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
325920	\N	Melinda	Kramer	4579	4332	2025-06-24 19:48:54.082673-05	nndz-WkNDL3diMy9oZz09	4513	t	\N	0	1	0.00		2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
325921	\N	Mary	Langhenry	4579	4332	2025-06-24 19:48:54.082673-05	nndz-WkNDL3diMzdqUT09	4513	t	\N	6	0	100.00		2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
325922	\N	Mary	Rafferty	4579	4332	2025-06-24 19:48:54.082673-05	nndz-WkNDOHlMYjhoQT09	4513	t	\N	3	5	37.50		2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
325923	\N	Elise	Soderlind-Moreno	4579	4332	2025-06-24 19:48:54.082673-05	nndz-WkM2eHhyNzhqUT09	4513	t	\N	7	1	87.50		2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
325924	\N	Janel	Palm	4579	4332	2025-06-24 19:48:54.082673-05	nndz-WkNDL3diMzhqQT09	4513	t	\N	4	4	50.00		2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
325925	\N	Adrienne	Regis	4579	4332	2025-06-24 19:48:54.082673-05	nndz-WkM2eHg3cndqQT09	4513	t	\N	5	3	62.50		2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
325926	\N	Christie	Simony	4579	4332	2025-06-24 19:48:54.082673-05	nndz-WkNHN3c3YjlqQT09	4513	t	\N	7	1	87.50		2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
325927	\N	Katie	Ojala	4579	4332	2025-06-24 19:48:54.082673-05	nndz-WkNHNXc3M3dnQT09	4513	t	\N	0	0	0.00		2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
325928	\N	Marie	Stensland	4579	4332	2025-06-24 19:48:54.082673-05	nndz-WkNHNHlMcjloQT09	4513	t	\N	4	1	80.00		2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
325929	\N	Laura	Eisen	4601	4332	2025-06-24 19:48:54.082673-05	nndz-WkNHNXhidndqUT09	4513	t	\N	2	3	40.00	CC	2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
325930	\N	Carly	Bernstein	4601	4332	2025-06-24 19:48:54.082673-05	nndz-WkMreHdiNy9ndz09	4513	t	\N	7	0	100.00		2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
325931	\N	Carrie	Feig	4601	4332	2025-06-24 19:48:54.082673-05	nndz-WkNHNXhiendodz09	4513	t	\N	0	5	0.00		2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
325932	\N	Kali	Friedmann	4601	4332	2025-06-24 19:48:54.082673-05	nndz-WkMreHdMdjdqUT09	4513	t	\N	5	3	62.50		2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
325933	\N	Traci	Hill	4601	4332	2025-06-24 19:48:54.082673-05	nndz-WkM2eHliLzhoQT09	4513	t	\N	4	3	57.10		2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
325934	\N	Amy	Kane	4601	4332	2025-06-24 19:48:54.082673-05	nndz-WkNDL3diL3hqUT09	4513	t	\N	1	3	25.00		2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
325935	\N	Jenny	Lev	4601	4332	2025-06-24 19:48:54.082673-05	nndz-WkM2eHliLzhoZz09	4513	t	\N	6	0	100.00		2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
325936	\N	Jeannie	Levy	4601	4332	2025-06-24 19:48:54.082673-05	nndz-WkM2eHhyM3hndz09	4513	t	\N	7	0	100.00		2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
325937	\N	Tracy	Miller	4601	4332	2025-06-24 19:48:54.082673-05	nndz-WkMrK3lMdjZqUT09	4513	t	\N	0	0	0.00		2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
325938	\N	Lindsay	Pessis	4601	4332	2025-06-24 19:48:54.082673-05	nndz-WkMreHdiMzRnZz09	4513	t	\N	5	5	50.00		2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
325939	\N	Carrie	Rose	4601	4332	2025-06-24 19:48:54.082673-05	nndz-WkM2eHhidjloQT09	4513	t	\N	4	6	40.00		2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
325940	\N	Chris	Fixler	4601	4332	2025-06-24 19:48:54.082673-05	nndz-WkMreHg3NzhnUT09	4513	t	\N	3	7	30.00		2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
325941	\N	Emily	Schwartz	4601	4332	2025-06-24 19:48:54.082673-05	nndz-WkM2eHhyM3hnZz09	4513	t	\N	3	8	27.30		2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
325942	\N	Robin	Miller	4601	4332	2025-06-24 19:48:54.082673-05	nndz-WlNlOXhMai9oQT09	4513	t	\N	1	7	12.50		2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
325943	\N	Erin	Pritzker	4601	4332	2025-06-24 19:48:54.082673-05	nndz-WlNlN3hyZi9ndz09	4513	t	\N	3	7	30.00		2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
325944	\N	Jacob	Groce	4612	4332	2025-06-24 19:48:54.082673-05	nndz-WkMreHdMdnhnZz09	4513	t	\N	0	0	0.00	C	2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
325945	\N	Andrea	Kroll	4612	4332	2025-06-24 19:48:54.082673-05	nndz-WkNHNXliN3dqQT09	4513	t	\N	1	8	11.10	CC	2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
325946	\N	Linda	Bronner	4612	4332	2025-06-24 19:48:54.082673-05	nndz-WkNDL3diMzRndz09	4513	t	\N	0	0	0.00		2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
325947	\N	Aly	Feder	4612	4332	2025-06-24 19:48:54.082673-05	nndz-WkNDL3diLzdqQT09	4513	t	\N	2	8	20.00		2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
325948	\N	Terri	Foster	4612	4332	2025-06-24 19:48:54.082673-05	nndz-WkM2eHg3YjRoQT09	4513	t	\N	0	2	0.00		2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
325949	\N	Julia	Gerstein	4612	4332	2025-06-24 19:48:54.082673-05	nndz-WkM2eHlMZi9nUT09	4513	t	\N	0	6	0.00		2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
325950	\N	Linda	Gerstman	4612	4332	2025-06-24 19:48:54.082673-05	nndz-WkNDOHlMZnhoUT09	4513	t	\N	1	4	20.00		2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
325951	\N	Marjorie	Jacobs	4612	4332	2025-06-24 19:48:54.082673-05	nndz-WkM2eHg3YjRodz09	4513	t	\N	1	2	33.30		2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
325952	\N	Megan	Kellerman	4612	4332	2025-06-24 19:48:54.082673-05	nndz-WlNlL3hiNzZoZz09	4513	t	\N	0	1	0.00		2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
325953	\N	Jacquie	Lewis	4612	4332	2025-06-24 19:48:54.082673-05	nndz-WkNDL3diLzZnUT09	4513	t	\N	0	0	0.00		2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
325954	\N	Helene	Nathan	4612	4332	2025-06-24 19:48:54.082673-05	nndz-WkNDL3diLzZoZz09	4513	t	\N	0	0	0.00		2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
325955	\N	Lindsay	Rotter	4612	4332	2025-06-24 19:48:54.082673-05	nndz-WkM2eHhycndnUT09	4513	t	\N	2	4	33.30		2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
325956	\N	Anna	Simon	4612	4332	2025-06-24 19:48:54.082673-05	nndz-WlNlNnlibi9oZz09	4513	t	\N	0	0	0.00		2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
325957	\N	Lee	Tresley	4612	4332	2025-06-24 19:48:54.082673-05	nndz-WkNDOHlMZitqQT09	4513	t	\N	1	1	50.00		2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
325958	\N	Brittany	Wilkow	4612	4332	2025-06-24 19:48:54.082673-05	nndz-WkMrNnc3ajhoUT09	4513	t	\N	0	0	0.00		2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
325959	\N	Michelle	Winterstein	4612	4332	2025-06-24 19:48:54.082673-05	nndz-WkM2eHhycndndz09	4513	t	\N	2	3	40.00		2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
325960	\N	Abby	Eisenberg	4612	4332	2025-06-24 19:48:54.082673-05	nndz-WkM2eHg3YjVqUT09	4513	t	\N	1	8	11.10		2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
325961	\N	Terry	Kass	4612	4332	2025-06-24 19:48:54.082673-05	nndz-WkM2eHg3YjRoZz09	4513	t	\N	0	2	0.00		2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
325962	\N	Allie	Davidson	4612	4332	2025-06-24 19:48:54.082673-05	nndz-WkNHN3dyMzRoQT09	4513	t	\N	0	1	0.00		2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
325963	\N	Shari	Field	4612	4332	2025-06-24 19:48:54.082673-05	nndz-WkNDL3diMzVqQT09	4513	t	\N	0	0	0.00		2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
325964	\N	Veronica	Moskow	4612	4332	2025-06-24 19:48:54.082673-05	nndz-WlNhK3dianhoZz09	4513	t	\N	0	0	0.00		2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
325965	\N	Jackie	Peltz	4612	4332	2025-06-24 19:48:54.082673-05	nndz-WkNDL3diMzRoUT09	4513	t	\N	0	0	0.00		2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
325966	\N	Heather	Crisman	4635	4332	2025-06-24 19:48:54.082673-05	nndz-WkM2eHg3ajlqQT09	4513	t	\N	2	5	28.60	C	2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
325967	\N	Elise	Duda	4635	4332	2025-06-24 19:48:54.082673-05	nndz-WkNHNXdMdjVoZz09	4513	t	\N	3	5	37.50	CC	2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
325968	\N	Elizabeth	Cimaroli	4635	4332	2025-06-24 19:48:54.082673-05	nndz-WkNDL3dicjdoQT09	4513	t	\N	1	6	14.30		2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
325969	\N	Ania	Cramer	4635	4332	2025-06-24 19:48:54.082673-05	nndz-WkNDL3dicnhnZz09	4513	t	\N	3	7	30.00		2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
325970	\N	katie	flanigan	4635	4332	2025-06-24 19:48:54.082673-05	nndz-WkNDL3didjhnQT09	4513	t	\N	4	4	50.00		2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
325971	\N	Sara	Kirkpatrick	4635	4332	2025-06-24 19:48:54.082673-05	nndz-WkNDL3diMzdoQT09	4513	t	\N	2	4	33.30		2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
325972	\N	Taylor	Oliver	4635	4332	2025-06-24 19:48:54.082673-05	nndz-WkM2eHg3ajhoQT09	4513	t	\N	1	7	12.50		2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
325973	\N	Leigh	Sears	4635	4332	2025-06-24 19:48:54.082673-05	nndz-WkNDL3diMy9nQT09	4513	t	\N	3	5	37.50		2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
325974	\N	Lee	Seftenberg	4635	4332	2025-06-24 19:48:54.082673-05	nndz-WkNDL3diN3hnQT09	4513	t	\N	2	5	28.60		2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
325975	\N	Sheila	Weimer	4635	4332	2025-06-24 19:48:54.082673-05	nndz-WkNDL3diN3hodz09	4513	t	\N	0	0	0.00		2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
325976	\N	Debbie	Frei	4635	4332	2025-06-24 19:48:54.082673-05	nndz-WkNHNHdiaitoZz09	4513	t	\N	3	7	30.00		2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
325977	\N	Margaret	Chaffee	4635	4332	2025-06-24 19:48:54.082673-05	nndz-WkMrK3c3YjVnQT09	4513	t	\N	3	4	42.90		2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
325978	\N	Melissa	David	4635	4332	2025-06-24 19:48:54.082673-05	nndz-WkNDL3diN3hqUT09	4513	t	\N	3	2	60.00		2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
325979	\N	Melissa	Yeoman	4639	4332	2025-06-24 19:48:54.082673-05	nndz-WkM2eHg3LzlnQT09	4513	t	\N	4	3	57.10	C	2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
325980	\N	Kelly	Brown	4639	4332	2025-06-24 19:48:54.082673-05	nndz-WkNHNHdiYjZnQT09	4513	t	\N	3	5	37.50	CC	2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
325981	\N	Molly	Champagne	4639	4332	2025-06-24 19:48:54.082673-05	nndz-WkM2eHg3ejhnQT09	4513	t	\N	6	1	85.70		2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
325982	\N	Kristen	Fox	4639	4332	2025-06-24 19:48:54.082673-05	nndz-WkMrL3lMajhoQT09	4513	t	\N	6	2	75.00		2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
325983	\N	Ann	Hagerty	4639	4332	2025-06-24 19:48:54.082673-05	nndz-WkNDeHdiL3doZz09	4513	t	\N	4	0	100.00		2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
325984	\N	Kim	Lombardo	4639	4332	2025-06-24 19:48:54.082673-05	nndz-WkNDL3diLzRnUT09	4513	t	\N	3	4	42.90		2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
325985	\N	Deirdre	Noshay	4639	4332	2025-06-24 19:48:54.082673-05	nndz-WkNDL3diLzRqUT09	4513	t	\N	5	3	62.50		2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
325986	\N	Shanna	Rose	4639	4332	2025-06-24 19:48:54.082673-05	nndz-WkMrK3dyZi9nUT09	4513	t	\N	6	4	60.00		2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
325987	\N	Lauren	Zambianchi	4639	4332	2025-06-24 19:48:54.082673-05	nndz-WkNHNXdMajZnZz09	4513	t	\N	3	4	42.90		2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
325988	\N	Meghan	Decker	4639	4332	2025-06-24 19:48:54.082673-05	nndz-WkMrK3dyci9oUT09	4513	t	\N	5	3	62.50		2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
325989	\N	Lauren	Bagull	4639	4332	2025-06-24 19:48:54.082673-05	nndz-WkM2eHhyYi9oQT09	4513	t	\N	1	2	33.30		2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
325990	\N	Sue	Fasciano	4639	4332	2025-06-24 19:48:54.082673-05	nndz-WkNDOHlMcndqUT09	4513	t	\N	0	0	0.00		2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
325991	\N	Linda	Finkel	4639	4332	2025-06-24 19:48:54.082673-05	nndz-WkNDOHlMZndoUT09	4513	t	\N	0	0	0.00		2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
325992	\N	Jessica	Gebauer	4639	4332	2025-06-24 19:48:54.082673-05	nndz-WkM2eHhyYndqUT09	4513	t	\N	3	4	42.90		2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
325993	\N	Sarah	Hayes	4639	4332	2025-06-24 19:48:54.082673-05	nndz-WkM2eHhyYjdndz09	4513	t	\N	4	4	50.00		2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
325994	\N	Libby	Hurley	4639	4332	2025-06-24 19:48:54.082673-05	nndz-WkMrK3diZjRnQT09	4513	t	\N	0	0	0.00		2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
325995	\N	Julie	Masini	4639	4332	2025-06-24 19:48:54.082673-05	nndz-WkNDOHlMcndoZz09	4513	t	\N	0	0	0.00		2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
325996	\N	Amanda	Kudrna	4639	4332	2025-06-24 19:48:54.082673-05	nndz-WlNlN3g3cjhnQT09	4513	t	\N	3	3	50.00		2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
325997	\N	Emily	Martensen	4639	4332	2025-06-24 19:48:54.082673-05	nndz-WkMrK3hiajdoZz09	4513	t	\N	4	4	50.00		2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
325998	\N	Carolyn	Moretti	4639	4332	2025-06-24 19:48:54.082673-05	nndz-WkM2eHhyZjRnZz09	4513	t	\N	6	4	60.00		2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
325999	\N	Tonya	Wheeler	4639	4332	2025-06-24 19:48:54.082673-05	nndz-WkM2eHhyZjVndz09	4513	t	\N	3	6	33.30		2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
326000	\N	Stephanie	Newton	4640	4332	2025-06-24 19:48:54.082673-05	nndz-WkNDL3diLzVnZz09	4513	t	\N	2	4	33.30	C	2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
326001	\N	Lynne	Hemmer	4640	4332	2025-06-24 19:48:54.082673-05	nndz-WkNDL3dicnhodz09	4513	t	\N	4	2	66.70	CC	2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
326002	\N	Cara	Andrus	4640	4332	2025-06-24 19:48:54.082673-05	nndz-WkNHNXc3cjhnUT09	4513	t	\N	4	1	80.00		2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
326003	\N	Mary	Beth Angelo	4640	4332	2025-06-24 19:48:54.082673-05	nndz-WkNHNXc3ci9nUT09	4513	t	\N	3	4	42.90		2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
326004	\N	Kim	Baker	4640	4332	2025-06-24 19:48:54.082673-05	nndz-WkM2eHg3ejhqUT09	4513	t	\N	2	8	20.00		2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
326005	\N	Daniela	Burnham	4640	4332	2025-06-24 19:48:54.082673-05	nndz-WkM2eHg3ei9oUT09	4513	t	\N	1	1	50.00		2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
326006	\N	Jacqueline	Hairston	4640	4332	2025-06-24 19:48:54.082673-05	nndz-WkNDL3dicitndz09	4513	t	\N	4	3	57.10		2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
326007	\N	Jennifer	Jacobson	4640	4332	2025-06-24 19:48:54.082673-05	nndz-WkNDL3dicitodz09	4513	t	\N	5	2	71.40		2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
326008	\N	Samantha	Pagels	4640	4332	2025-06-24 19:48:54.082673-05	nndz-WkNDL3dicitnQT09	4513	t	\N	5	2	71.40		2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
326009	\N	Jordan	Shackleford	4640	4332	2025-06-24 19:48:54.082673-05	nndz-WkM2eHg3ejhqQT09	4513	t	\N	2	1	66.70		2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
326010	\N	Daniella	Watkins	4640	4332	2025-06-24 19:48:54.082673-05	nndz-WkM2eHliNzRqUT09	4513	t	\N	4	7	36.40		2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
326011	\N	Kristy	Brown	4640	4332	2025-06-24 19:48:54.082673-05	nndz-WkM2eHhyZitnQT09	4513	t	\N	7	1	87.50		2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
326012	\N	Adrienne	Eynon	4640	4332	2025-06-24 19:48:54.082673-05	nndz-WkM2eHhyZndodz09	4513	t	\N	13	4	76.50		2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
326013	\N	Amy	Gelwix	4640	4332	2025-06-24 19:48:54.082673-05	nndz-WkM2eHliNzRoQT09	4513	t	\N	6	1	85.70		2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
326014	\N	Mary	Jo Lestingi	4640	4332	2025-06-24 19:48:54.082673-05	nndz-WkM2eHg3ejZodz09	4513	t	\N	2	1	66.70		2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
326015	\N	REBECCA	WADMAN	4640	4332	2025-06-24 19:48:54.082673-05	nndz-WlNlN3hiNzRoZz09	4513	t	\N	11	1	91.70		2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
326016	\N	Mary	White	4640	4332	2025-06-24 19:48:54.082673-05	nndz-WkM2eHhyZitnUT09	4513	t	\N	3	1	75.00		2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
326017	\N	Amanda	Doblin	4642	4332	2025-06-24 19:48:54.082673-05	nndz-WkNHNXhyandoZz09	4513	t	\N	4	7	36.40	C	2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
326018	\N	Darshana	Lele	4642	4332	2025-06-24 19:48:54.082673-05	nndz-WkM2eHliNzVnZz09	4513	t	\N	3	2	60.00	CC	2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
326019	\N	Kelly	Bireley	4642	4332	2025-06-24 19:48:54.082673-05	nndz-WkM2eHliNzVoZz09	4513	t	\N	1	5	16.70		2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
326020	\N	Aimee	Koski	4642	4332	2025-06-24 19:48:54.082673-05	nndz-WkM2eHliNzVndz09	4513	t	\N	8	4	66.70		2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
326021	\N	Linda	McKenzie	4642	4332	2025-06-24 19:48:54.082673-05	nndz-WkNDOHlMZitnUT09	4513	t	\N	0	0	0.00		2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
326022	\N	Dana	McLaughlin	4642	4332	2025-06-24 19:48:54.082673-05	nndz-WkNHNXdyZitnZz09	4513	t	\N	4	3	57.10		2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
326023	\N	Anna	Petric	4642	4332	2025-06-24 19:48:54.082673-05	nndz-WlNlN3diejRoUT09	4513	t	\N	8	3	72.70		2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
326024	\N	Laurie	Siok	4642	4332	2025-06-24 19:48:54.082673-05	nndz-WkM2eHliNzVqUT09	4513	t	\N	7	5	58.30		2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
326025	\N	Brandy	Todd	4642	4332	2025-06-24 19:48:54.082673-05	nndz-WkNHNXdyZitoZz09	4513	t	\N	1	6	14.30		2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
326026	\N	Laura	Pine	4642	4332	2025-06-24 19:48:54.082673-05	nndz-WkMrK3lMenhqUT09	4513	t	\N	2	5	28.60		2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
326027	\N	Megan	Ausenbaugh	4642	4332	2025-06-24 19:48:54.082673-05	nndz-WkMrK3lMbjVoZz09	4513	t	\N	5	3	62.50		2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
326028	\N	Maggie	Burke	4642	4332	2025-06-24 19:48:54.082673-05	nndz-WkMreHdMLzVqQT09	4513	t	\N	13	1	92.90		2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
326029	\N	Erin	Heywood	4642	4332	2025-06-24 19:48:54.082673-05	nndz-WkMreHdMNzZoZz09	4513	t	\N	6	2	75.00		2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
326030	\N	Alexis	Kuncel	4642	4332	2025-06-24 19:48:54.082673-05	nndz-WkMreHdMLzRnQT09	4513	t	\N	5	1	83.30		2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
326031	\N	Annie	Smith	4642	4332	2025-06-24 19:48:54.082673-05	nndz-WkMrK3hidjZnZz09	4513	t	\N	12	1	92.30		2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
326032	\N	Laura	Wayland	4642	4332	2025-06-24 19:48:54.082673-05	nndz-WkM2eHliN3dqQT09	4513	t	\N	5	10	33.30		2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
326033	\N	Beth	Wechsler	4642	4332	2025-06-24 19:48:54.082673-05	nndz-WkMreHdiZjhnUT09	4513	t	\N	7	2	77.80		2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
326034	\N	Lizzy	Cohen	4571	4333	2025-06-24 19:48:54.082673-05	nndz-WkNHNXdyejloZz09	4513	t	\N	1	5	16.70	C	2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
326035	\N	Lisa	Dorfman	4571	4333	2025-06-24 19:48:54.082673-05	nndz-WkM2eHhyNzRoZz09	4513	t	\N	0	9	0.00	CC	2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
326036	\N	Carrie	Block	4571	4333	2025-06-24 19:48:54.082673-05	nndz-WkNHNXdyejlndz09	4513	t	\N	0	7	0.00		2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
326037	\N	Jessica	Cohen	4571	4333	2025-06-24 19:48:54.082673-05	nndz-WkM2eHhyNzRoQT09	4513	t	\N	0	6	0.00		2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
326038	\N	Julie	Feldman	4571	4333	2025-06-24 19:48:54.082673-05	nndz-WkM2eHhybjRqUT09	4513	t	\N	4	3	57.10		2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
326039	\N	Taryn	Kessel	4571	4333	2025-06-24 19:48:54.082673-05	nndz-WkNDL3diMzZnZz09	4513	t	\N	0	3	0.00		2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
326040	\N	Susan	Pasternak	4571	4333	2025-06-24 19:48:54.082673-05	nndz-WkNHNXdyejdnZz09	4513	t	\N	1	1	50.00		2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
326041	\N	Jill	Rowe	4571	4333	2025-06-24 19:48:54.082673-05	nndz-WkNDL3didnhodz09	4513	t	\N	4	4	50.00		2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
326042	\N	Danielle	Schwartz	4571	4333	2025-06-24 19:48:54.082673-05	nndz-WkM2eHhyNzVnZz09	4513	t	\N	1	5	16.70		2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
326043	\N	Dawn	Von Samek	4571	4333	2025-06-24 19:48:54.082673-05	nndz-WkNDL3didi9qUT09	4513	t	\N	0	5	0.00		2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
326044	\N	lyn	wise	4571	4333	2025-06-24 19:48:54.082673-05	nndz-WkNDL3dieitnZz09	4513	t	\N	1	5	16.70		2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
326045	\N	Ivy	Domont	4571	4333	2025-06-24 19:48:54.082673-05	nndz-WkM2eHhyNzRodz09	4513	t	\N	2	5	28.60		2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
326046	\N	Margalit	Feiger	4571	4333	2025-06-24 19:48:54.082673-05	nndz-WkM2eHhyNzdoUT09	4513	t	\N	1	6	14.30		2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
326047	\N	Lauren	Kase	4571	4333	2025-06-24 19:48:54.082673-05	nndz-WkM2eHhyNzRnUT09	4513	t	\N	2	6	25.00		2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
326048	\N	Marny	Kravenas	4571	4333	2025-06-24 19:48:54.082673-05	nndz-WkM2eHg3anhndz09	4513	t	\N	6	4	60.00		2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
326049	\N	Stacey	Price	4571	4333	2025-06-24 19:48:54.082673-05	nndz-WkM2eHhyNzRnQT09	4513	t	\N	3	2	60.00		2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
326050	\N	Heidi	Sachs	4571	4333	2025-06-24 19:48:54.082673-05	nndz-WkM2eHhyNzRndz09	4513	t	\N	7	4	63.60		2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
326051	\N	Cristy	Steinberg	4571	4333	2025-06-24 19:48:54.082673-05	nndz-WkNDL3didnhoZz09	4513	t	\N	0	2	0.00		2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
326052	\N	Vicki	Bernstein	4574	4333	2025-06-24 19:48:54.082673-05	nndz-WkNDeHdiLzlqUT09	4513	t	\N	0	0	0.00	C	2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
326053	\N	Sara	Fisher	4574	4333	2025-06-24 19:48:54.082673-05	nndz-WkMrK3dMNzZodz09	4513	t	\N	3	4	42.90	CC	2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
326054	\N	Wendy	Bremen	4574	4333	2025-06-24 19:48:54.082673-05	nndz-WkNDOHlMbjlnQT09	4513	t	\N	5	2	71.40		2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
326055	\N	Barrie	Hananel	4574	4333	2025-06-24 19:48:54.082673-05	nndz-WlNlNnhyNzdqUT09	4513	t	\N	3	3	50.00		2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
326056	\N	Tracie	Harris	4574	4333	2025-06-24 19:48:54.082673-05	nndz-WkMrK3hMcjlqUT09	4513	t	\N	3	1	75.00		2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
326057	\N	Emily	Hoffman	4574	4333	2025-06-24 19:48:54.082673-05	nndz-WkMrL3lMZjlndz09	4513	t	\N	2	2	50.00		2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
326058	\N	Karen	Jaffe	4574	4333	2025-06-24 19:48:54.082673-05	nndz-WlNhOXdiYi9nZz09	4513	t	\N	4	3	57.10		2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
326059	\N	Hope	Katz	4574	4333	2025-06-24 19:48:54.082673-05	nndz-WkMrK3lMN3doQT09	4513	t	\N	5	0	100.00		2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
326060	\N	Rachel	Katz	4574	4333	2025-06-24 19:48:54.082673-05	nndz-WkMrK3dybndoQT09	4513	t	\N	1	2	33.30		2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
326061	\N	Schuyler	Levin	4574	4333	2025-06-24 19:48:54.082673-05	nndz-WkMrK3diM3doUT09	4513	t	\N	4	1	80.00		2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
326062	\N	Emily	Rotenberg	4574	4333	2025-06-24 19:48:54.082673-05	nndz-WkMrK3hMcjlqQT09	4513	t	\N	5	2	71.40		2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
326063	\N	Dana	Singerman	4574	4333	2025-06-24 19:48:54.082673-05	nndz-WkMrK3dybnhodz09	4513	t	\N	3	3	50.00		2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
326064	\N	Rebecca	Graines	4574	4333	2025-06-24 19:48:54.082673-05	nndz-WkMrK3dybitnQT09	4513	t	\N	4	3	57.10		2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
326065	\N	Debra	kissen	4574	4333	2025-06-24 19:48:54.082673-05	nndz-WlNlN3diNy9oQT09	4513	t	\N	6	1	85.70		2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
326066	\N	Lynne	Levey	4574	4333	2025-06-24 19:48:54.082673-05	nndz-WlNlN3g3cnhodz09	4513	t	\N	4	3	57.10		2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
326067	\N	Marcy	Zoller	4574	4333	2025-06-24 19:48:54.082673-05	nndz-WkMrK3g3cjZodz09	4513	t	\N	4	4	50.00		2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
326068	\N	Rebecca	Krizmanich	4579	4333	2025-06-24 19:48:54.082673-05	nndz-WkM2eHg3aitoZz09	4513	t	\N	2	2	50.00	C	2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
326069	\N	Gretchen	Cappiello	4579	4333	2025-06-24 19:48:54.082673-05	nndz-WkNDeHdiNzVnUT09	4513	t	\N	2	4	33.30	CC	2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
326070	\N	Tessa	Bediz	4579	4333	2025-06-24 19:48:54.082673-05	nndz-WkM2eHhyNzlnZz09	4513	t	\N	0	7	0.00		2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
326071	\N	Jennifer	Bergquist	4579	4333	2025-06-24 19:48:54.082673-05	nndz-WkNHNXc3M3hqQT09	4513	t	\N	0	0	0.00		2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
326072	\N	Emily	Hoffman - EGC	4579	4333	2025-06-24 19:48:54.082673-05	nndz-WkNDL3diMzZndz09	4513	t	\N	1	7	12.50		2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
326073	\N	Becky	Huston	4579	4333	2025-06-24 19:48:54.082673-05	nndz-WkNDL3diMzloUT09	4513	t	\N	0	6	0.00		2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
326074	\N	Meghann	Kohli	4579	4333	2025-06-24 19:48:54.082673-05	nndz-WkM2eHhyNzhodz09	4513	t	\N	5	3	62.50		2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
326075	\N	Rachel	Pasquini	4579	4333	2025-06-24 19:48:54.082673-05	nndz-WkM2eHhyNy9nQT09	4513	t	\N	5	3	62.50		2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
326076	\N	Kathi	Samuels	4579	4333	2025-06-24 19:48:54.082673-05	nndz-WkM2eHhyNzhndz09	4513	t	\N	3	2	60.00		2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
326077	\N	Theresa	Smith	4579	4333	2025-06-24 19:48:54.082673-05	nndz-WkM2eHhyNy9nZz09	4513	t	\N	3	3	50.00		2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
326078	\N	Laura	Steinhandler	4579	4333	2025-06-24 19:48:54.082673-05	nndz-WkM2eHg3aitodz09	4513	t	\N	3	3	50.00		2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
326079	\N	Bridget	Whisdosh	4579	4333	2025-06-24 19:48:54.082673-05	nndz-WkM2eHhyNzhoUT09	4513	t	\N	2	5	28.60		2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
326080	\N	Allison	Angeloni	4579	4333	2025-06-24 19:48:54.082673-05	nndz-WkM2eHhyN3dnUT09	4513	t	\N	6	6	50.00		2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
326081	\N	Anne	Murdoch	4579	4333	2025-06-24 19:48:54.082673-05	nndz-WkM2eHhyNzhnUT09	4513	t	\N	6	3	66.70		2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
326082	\N	Taylor	Rosellini	4579	4333	2025-06-24 19:48:54.082673-05	nndz-WkM2eHhyLzVoZz09	4513	t	\N	5	3	62.50		2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
326083	\N	Nicole	Holson	4595	4333	2025-06-24 19:48:54.082673-05	nndz-WkM2eHhyejhodz09	4513	t	\N	2	6	25.00	C	2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
326084	\N	Kelly	Scott	4595	4333	2025-06-24 19:48:54.082673-05	nndz-WkM2eHhyejhqUT09	4513	t	\N	3	5	37.50	CC	2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
326085	\N	Lindsay	Bianco	4595	4333	2025-06-24 19:48:54.082673-05	nndz-WkM2eHhyejlqUT09	4513	t	\N	4	1	80.00		2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
326086	\N	Erin	Buelt	4595	4333	2025-06-24 19:48:54.082673-05	nndz-WkM2eHhyMzRoZz09	4513	t	\N	7	1	87.50		2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
326087	\N	Jane	Duncan	4595	4333	2025-06-24 19:48:54.082673-05	nndz-WkM2eHhyei9odz09	4513	t	\N	4	1	80.00		2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
326088	\N	Lauren	Perkaus	4595	4333	2025-06-24 19:48:54.082673-05	nndz-WkM2eHhyejhndz09	4513	t	\N	2	0	100.00		2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
326089	\N	Becky	Weitzel	4595	4333	2025-06-24 19:48:54.082673-05	nndz-WkM2eHhyei9oUT09	4513	t	\N	6	2	75.00		2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
326090	\N	Simone	Asmussen	4595	4333	2025-06-24 19:48:54.082673-05	nndz-WkNHNXdMM3hnQT09	4513	t	\N	0	2	0.00		2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
326091	\N	Tammy	Fiordaliso	4595	4333	2025-06-24 19:48:54.082673-05	nndz-WkNDL3diL3dnZz09	4513	t	\N	5	1	83.30		2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
326092	\N	Joan	Giangiorgi	4595	4333	2025-06-24 19:48:54.082673-05	nndz-WkNDL3dicjZnZz09	4513	t	\N	2	1	66.70		2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
326093	\N	Lynn	Jensen	4595	4333	2025-06-24 19:48:54.082673-05	nndz-WkNHNXdMcjVoUT09	4513	t	\N	3	3	50.00		2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
326094	\N	Julie	Ward	4595	4333	2025-06-24 19:48:54.082673-05	nndz-WkNDL3diL3dnUT09	4513	t	\N	4	3	57.10		2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
326095	\N	Donna	Oldenburg	4595	4333	2025-06-24 19:48:54.082673-05	nndz-WkNHNXdyLzVnUT09	4513	t	\N	0	0	0.00		2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
326096	\N	Mila	Sobinsky	4595	4333	2025-06-24 19:48:54.082673-05	nndz-WkM2eHhyejhqQT09	4513	t	\N	1	8	11.10		2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
326097	\N	Anne	Moebius	4600	4333	2025-06-24 19:48:54.082673-05	nndz-WkNDL3dienhoQT09	4513	t	\N	7	4	63.60	C	2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
326098	\N	Pam	Kleinert	4600	4333	2025-06-24 19:48:54.082673-05	nndz-WkNDOHlML3dndz09	4513	t	\N	3	5	37.50		2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
326099	\N	Laura	Lance	4600	4333	2025-06-24 19:48:54.082673-05	nndz-WlNlOXc3M3hnZz09	4513	t	\N	2	2	50.00		2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
326100	\N	Debbie	Marcusson	4600	4333	2025-06-24 19:48:54.082673-05	nndz-WkNDL3diLzhnZz09	4513	t	\N	6	2	75.00		2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
326101	\N	Katie	McClelland	4600	4333	2025-06-24 19:48:54.082673-05	nndz-WkNDL3diMy9ndz09	4513	t	\N	5	4	55.60		2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
326102	\N	Irene	Okada	4600	4333	2025-06-24 19:48:54.082673-05	nndz-WkM2eHhyendqQT09	4513	t	\N	5	3	62.50		2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
326103	\N	Jamie	Rauscher	4600	4333	2025-06-24 19:48:54.082673-05	nndz-WkNHNXc3cnhqQT09	4513	t	\N	7	2	77.80		2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
326104	\N	Cyncy	Schacher	4600	4333	2025-06-24 19:48:54.082673-05	nndz-WkNDOHlMZjlnZz09	4513	t	\N	1	0	100.00		2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
326105	\N	Madeleine	Slingerland	4600	4333	2025-06-24 19:48:54.082673-05	nndz-WkNDOHlMZjdodz09	4513	t	\N	4	4	50.00		2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
326106	\N	Liz	Biddle	4600	4333	2025-06-24 19:48:54.082673-05	nndz-WkNDOHlMZjhoQT09	4513	t	\N	3	3	50.00		2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
326107	\N	Sharla	Mick	4600	4333	2025-06-24 19:48:54.082673-05	nndz-WkNDK3lMZndoZz09	4513	t	\N	0	0	0.00		2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
326108	\N	Kateri	Rapport	4600	4333	2025-06-24 19:48:54.082673-05	nndz-WkMrK3hMYjZqQT09	4513	t	\N	2	0	100.00		2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
326109	\N	Julie	Mielzynski	4600	4333	2025-06-24 19:48:54.082673-05	nndz-WkM2eHhyMzVnQT09	4513	t	\N	1	2	33.30		2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
326110	\N	Paige	Newhouse	4600	4333	2025-06-24 19:48:54.082673-05	nndz-WkM2eHg3Lzdodz09	4513	t	\N	1	4	20.00		2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
326111	\N	Ellie	Schwab	4600	4333	2025-06-24 19:48:54.082673-05	nndz-WkM2eHhyMzlnUT09	4513	t	\N	2	6	25.00		2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
326112	\N	Kait	Soave	4600	4333	2025-06-24 19:48:54.082673-05	nndz-WkMrK3hidjZqQT09	4513	t	\N	1	7	12.50		2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
326113	\N	Kathy	Manny	4618	4333	2025-06-24 19:48:54.082673-05	nndz-WkNHNXdyZjRqUT09	4513	t	\N	3	5	37.50	C	2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
326114	\N	Arrika	Kris Schneider	4618	4333	2025-06-24 19:48:54.082673-05	nndz-WkM2eHhydjRoZz09	4513	t	\N	4	8	33.30	CC	2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
326115	\N	Mary	Denicolo	4618	4333	2025-06-24 19:48:54.082673-05	nndz-WkM2eHhydjVnZz09	4513	t	\N	6	2	75.00		2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
326116	\N	Amber	Fleura	4618	4333	2025-06-24 19:48:54.082673-05	nndz-WkM2eHhydjVqUT09	4513	t	\N	6	2	75.00		2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
326117	\N	Amanda	Hill	4618	4333	2025-06-24 19:48:54.082673-05	nndz-WkM2eHhydjVqQT09	4513	t	\N	2	3	40.00		2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
326118	\N	Angie	Keane	4618	4333	2025-06-24 19:48:54.082673-05	nndz-WkM2d3hMcjRnUT09	4513	t	\N	5	1	83.30		2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
326119	\N	Kim	Keyworth	4618	4333	2025-06-24 19:48:54.082673-05	nndz-WkMrK3liLzlqQT09	4513	t	\N	2	1	66.70		2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
326120	\N	Pamela	Larson	4618	4333	2025-06-24 19:48:54.082673-05	nndz-WkMrK3c3YjZoZz09	4513	t	\N	4	4	50.00		2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
326121	\N	Dorai	Lennon	4618	4333	2025-06-24 19:48:54.082673-05	nndz-WkNHNXdyNy9qUT09	4513	t	\N	3	3	50.00		2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
326122	\N	Mary	McGeean	4618	4333	2025-06-24 19:48:54.082673-05	nndz-WkMrK3c3NzZqUT09	4513	t	\N	4	2	66.70		2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
326123	\N	Sara	Press	4618	4333	2025-06-24 19:48:54.082673-05	nndz-WkNHNXdyNzhndz09	4513	t	\N	4	2	66.70		2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
326124	\N	Sarah	Walter	4618	4333	2025-06-24 19:48:54.082673-05	nndz-WkM2eHhydjRnZz09	4513	t	\N	4	1	80.00		2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
326125	\N	Meghan	Buckman	4618	4333	2025-06-24 19:48:54.082673-05	nndz-WkMrK3dMbndqQT09	4513	t	\N	6	4	60.00		2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
326126	\N	Sara	Daul	4618	4333	2025-06-24 19:48:54.082673-05	nndz-WkMrK3dMN3hnQT09	4513	t	\N	6	0	100.00		2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
326127	\N	Marissa	DiFranco	4618	4333	2025-06-24 19:48:54.082673-05	nndz-WkMrL3lMLzlnUT09	4513	t	\N	6	11	35.30		2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
326128	\N	Annie	Heigl	4618	4333	2025-06-24 19:48:54.082673-05	nndz-WkMrK3dMNytnUT09	4513	t	\N	8	2	80.00		2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
326129	\N	Mary	Manganaro	4618	4333	2025-06-24 19:48:54.082673-05	nndz-WkMrK3dicitoQT09	4513	t	\N	6	2	75.00		2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
326130	\N	Amanda	Rafferty	4618	4333	2025-06-24 19:48:54.082673-05	nndz-WkNHNXdyNytoZz09	4513	t	\N	2	5	28.60		2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
326131	\N	Inna	Elterman	4631	4333	2025-06-24 19:48:54.082673-05	nndz-WkNDL3diLzVoZz09	4513	t	\N	7	2	77.80	C	2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
326132	\N	Jancy	Audet	4631	4333	2025-06-24 19:48:54.082673-05	nndz-WkMrK3dMNytqQT09	4513	t	\N	0	0	0.00		2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
326133	\N	Rachel	Barner	4631	4333	2025-06-24 19:48:54.082673-05	nndz-WkM2eHhyajRoQT09	4513	t	\N	0	0	0.00		2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
326134	\N	Katie	Berger	4631	4333	2025-06-24 19:48:54.082673-05	nndz-WlNlL3c3Ly9odz09	4513	t	\N	0	2	0.00		2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
326135	\N	Michelle	Buzby	4631	4333	2025-06-24 19:48:54.082673-05	nndz-WkNHNXhiNzRoQT09	4513	t	\N	2	2	50.00		2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
326136	\N	Isabel	Carpenter	4631	4333	2025-06-24 19:48:54.082673-05	nndz-WkMrK3hiajdnZz09	4513	t	\N	0	3	0.00		2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
326137	\N	jeanette	cutler	4631	4333	2025-06-24 19:48:54.082673-05	nndz-WlNlNng3Yi9nQT09	4513	t	\N	0	0	0.00		2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
326138	\N	Sarah	Gallagher	4631	4333	2025-06-24 19:48:54.082673-05	nndz-WkM2eHhyajRnQT09	4513	t	\N	0	0	0.00		2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
326139	\N	Kirste	Gaudet	4631	4333	2025-06-24 19:48:54.082673-05	nndz-WlNlNnlMYjdndz09	4513	t	\N	6	2	75.00		2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
326140	\N	Marie	Geanuleas	4631	4333	2025-06-24 19:48:54.082673-05	nndz-WkMreHdMdjloZz09	4513	t	\N	2	2	50.00		2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
326141	\N	Susan	Geraghty	4631	4333	2025-06-24 19:48:54.082673-05	nndz-WlNlL3dibjhoUT09	4513	t	\N	0	3	0.00		2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
326142	\N	Sophie	Goodwillie	4631	4333	2025-06-24 19:48:54.082673-05	nndz-WkMreHdiZjZnQT09	4513	t	\N	0	0	0.00		2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
326143	\N	Lena	Helms	4631	4333	2025-06-24 19:48:54.082673-05	nndz-WkNHNXhMMy9nQT09	4513	t	\N	0	0	0.00		2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
326144	\N	Angie	Holleb	4631	4333	2025-06-24 19:48:54.082673-05	nndz-WlNlNnliejRoZz09	4513	t	\N	4	3	57.10		2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
326145	\N	Kelly	Kurschner	4631	4333	2025-06-24 19:48:54.082673-05	nndz-WkNDOHlMZjlqQT09	4513	t	\N	0	0	0.00		2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
326146	\N	Liz	McCarthy	4631	4333	2025-06-24 19:48:54.082673-05	nndz-WkNHNXhiNzRoUT09	4513	t	\N	0	0	0.00		2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
326147	\N	Dana	Pearce	4631	4333	2025-06-24 19:48:54.082673-05	nndz-WkM2eHhyN3doUT09	4513	t	\N	0	0	0.00		2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
326148	\N	Dianne	Sauvage	4631	4333	2025-06-24 19:48:54.082673-05	nndz-WkNHNXhiNzVnZz09	4513	t	\N	0	2	0.00		2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
326149	\N	Kira	Schenk	4631	4333	2025-06-24 19:48:54.082673-05	nndz-WkNHNXhiNzVqUT09	4513	t	\N	0	0	0.00		2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
326150	\N	Gabrielle	Schwertfeger	4631	4333	2025-06-24 19:48:54.082673-05	nndz-WlNlN3hyM3dnZz09	4513	t	\N	1	2	33.30		2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
326151	\N	Julie	Simon	4631	4333	2025-06-24 19:48:54.082673-05	nndz-WkM2eHhyajRqUT09	4513	t	\N	4	3	57.10		2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
326152	\N	Kirsten	Villers	4631	4333	2025-06-24 19:48:54.082673-05	nndz-WkMrK3dMYjloUT09	4513	t	\N	4	4	50.00		2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
326153	\N	Courtney	Johnson	4631	4333	2025-06-24 19:48:54.082673-05	nndz-WlNlOXhMZnhoUT09	4513	t	\N	4	0	100.00		2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
326154	\N	Lisa	Wagner	4638	4333	2025-06-24 19:48:54.082673-05	nndz-WkM2eHhybi9qUT09	4513	t	\N	1	6	14.30	C	2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
326155	\N	Lindsey	Lieberman	4638	4333	2025-06-24 19:48:54.082673-05	nndz-WkMrK3dMNzdnQT09	4513	t	\N	1	6	14.30	CC	2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
326156	\N	Beth	Arenberg	4638	4333	2025-06-24 19:48:54.082673-05	nndz-WkM2eHhybi9qQT09	4513	t	\N	1	4	20.00		2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
326157	\N	Natalie	Cohen	4638	4333	2025-06-24 19:48:54.082673-05	nndz-WkM2eHhybjRndz09	4513	t	\N	1	6	14.30		2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
326158	\N	Vanessa	Fjeldheim	4638	4333	2025-06-24 19:48:54.082673-05	nndz-WkM2eHhybjdnQT09	4513	t	\N	1	6	14.30		2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
326159	\N	Jennifer	Frank	4638	4333	2025-06-24 19:48:54.082673-05	nndz-WkM2eHhybitnUT09	4513	t	\N	1	5	16.70		2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
326160	\N	Amy	Kaske Berger	4638	4333	2025-06-24 19:48:54.082673-05	nndz-WkMrL3lMajVndz09	4513	t	\N	1	5	16.70		2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
326161	\N	Ellen	Razzoog	4638	4333	2025-06-24 19:48:54.082673-05	nndz-WkM2eHhybnhodz09	4513	t	\N	0	5	0.00		2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
326162	\N	Carly	Rosenthal	4638	4333	2025-06-24 19:48:54.082673-05	nndz-WkMrK3dydjZoUT09	4513	t	\N	2	3	40.00		2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
326163	\N	Dana	Shefren	4638	4333	2025-06-24 19:48:54.082673-05	nndz-WkMrK3dMajdnUT09	4513	t	\N	2	4	33.30		2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
326164	\N	Kristina	Stevens	4638	4333	2025-06-24 19:48:54.082673-05	nndz-WkM2eHhybjdoZz09	4513	t	\N	0	4	0.00		2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
326165	\N	Donnie	Stutland	4638	4333	2025-06-24 19:48:54.082673-05	nndz-WkM2eHhybjZoUT09	4513	t	\N	1	3	25.00		2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
326166	\N	Hien	Lyons	4638	4333	2025-06-24 19:48:54.082673-05	nndz-WkM2eHhybjdndz09	4513	t	\N	3	1	75.00		2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
326167	\N	Laura	Skale	4638	4333	2025-06-24 19:48:54.082673-05	nndz-WkMrK3dibjhqUT09	4513	t	\N	3	3	50.00		2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
326168	\N	Lisa	Boots	4646	4333	2025-06-24 19:48:54.082673-05	nndz-WkM2eHhidjlnUT09	4513	t	\N	6	2	75.00	C	2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
326169	\N	Lori	Schretzman	4646	4333	2025-06-24 19:48:54.082673-05	nndz-WkNDL3diM3dqQT09	4513	t	\N	4	3	57.10	CC	2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
326170	\N	Kelly	Coughlin	4646	4333	2025-06-24 19:48:54.082673-05	nndz-WkNDL3diMzlqUT09	4513	t	\N	6	1	85.70		2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
326171	\N	Andrea	deVos	4646	4333	2025-06-24 19:48:54.082673-05	nndz-WkMrK3dMMy9nQT09	4513	t	\N	5	0	100.00		2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
326172	\N	Elizabeth	Gallagher	4646	4333	2025-06-24 19:48:54.082673-05	nndz-WkM2eHhidjlqQT09	4513	t	\N	6	0	100.00		2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
326173	\N	Shannon	Hiltabrand	4646	4333	2025-06-24 19:48:54.082673-05	nndz-WkNDOHlMZjhoZz09	4513	t	\N	5	3	62.50		2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
326174	\N	Brie	Root	4646	4333	2025-06-24 19:48:54.082673-05	nndz-WkNDL3diLy9nUT09	4513	t	\N	6	1	85.70		2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
326175	\N	Colleen	Walker	4646	4333	2025-06-24 19:48:54.082673-05	nndz-WkNDL3diM3hqUT09	4513	t	\N	4	1	80.00		2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
326176	\N	Jackie	Rosinus	4646	4333	2025-06-24 19:48:54.082673-05	nndz-WkNHNHliZitoZz09	4513	t	\N	8	2	80.00		2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
326177	\N	Samantha	Weinberg	4646	4333	2025-06-24 19:48:54.082673-05	nndz-WkMrK3hiajRqQT09	4513	t	\N	8	3	72.70		2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
326178	\N	Alison	Marino	4646	4333	2025-06-24 19:48:54.082673-05	nndz-WkMrK3diM3hodz09	4513	t	\N	10	3	76.90		2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
326179	\N	Anne	Sullivan	4646	4333	2025-06-24 19:48:54.082673-05	nndz-WkM2eHhidjZnQT09	4513	t	\N	1	0	100.00		2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
326180	\N	Julie	Booma	4649	4333	2025-06-24 19:48:54.082673-05	nndz-WkM2d3hiZjZnQT09	4513	t	\N	4	4	50.00	C	2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
326181	\N	Chrissy	Siemen	4649	4333	2025-06-24 19:48:54.082673-05	nndz-WkM2eHliejVoQT09	4513	t	\N	5	4	55.60	CC	2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
326182	\N	Victoria	Bozic	4649	4333	2025-06-24 19:48:54.082673-05	nndz-WkM2eHliL3dndz09	4513	t	\N	6	2	75.00		2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
326183	\N	Laura	Breakstone	4649	4333	2025-06-24 19:48:54.082673-05	nndz-WkM2eHliL3dnZz09	4513	t	\N	5	5	50.00		2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
326184	\N	Kirstin	Carruthers	4649	4333	2025-06-24 19:48:54.082673-05	nndz-WkNDL3didndndz09	4513	t	\N	5	2	71.40		2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
326185	\N	Rachel	Karnani	4649	4333	2025-06-24 19:48:54.082673-05	nndz-WkM2eHliL3dqUT09	4513	t	\N	0	0	0.00		2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
326186	\N	Andrea	Lockhart	4649	4333	2025-06-24 19:48:54.082673-05	nndz-WkM2eHliL3dqQT09	4513	t	\N	3	4	42.90		2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
326187	\N	Jennifer	Manning	4649	4333	2025-06-24 19:48:54.082673-05	nndz-WkM2eHhyMytndz09	4513	t	\N	4	4	50.00		2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
326188	\N	Pamela	Metz	4649	4333	2025-06-24 19:48:54.082673-05	nndz-WkM2eHg3ajhoZz09	4513	t	\N	1	3	25.00		2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
326189	\N	Christine	Reinhardt	4649	4333	2025-06-24 19:48:54.082673-05	nndz-WkNHNXlMMzZoZz09	4513	t	\N	0	3	0.00		2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
326190	\N	Ann	Rieder	4649	4333	2025-06-24 19:48:54.082673-05	nndz-WkM2eHliejhoUT09	4513	t	\N	1	4	20.00		2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
326191	\N	Sam	Trace	4649	4333	2025-06-24 19:48:54.082673-05	nndz-WkM2eHhyM3hoQT09	4513	t	\N	0	3	0.00		2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
326192	\N	Kathrin	Martens-Salgat	4649	4333	2025-06-24 19:48:54.082673-05	nndz-WkMrK3hMMy9nUT09	4513	t	\N	7	6	53.80		2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
326193	\N	Amy	Miclea	4649	4333	2025-06-24 19:48:54.082673-05	nndz-WlNhNnliMzhodz09	4513	t	\N	13	0	100.00		2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
326194	\N	Lauren	Kase	4571	4334	2025-06-24 19:48:54.082673-05	nndz-WkM2eHhyNzRnUT09	4513	t	\N	2	6	25.00	C	2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
326195	\N	Marny	Kravenas	4571	4334	2025-06-24 19:48:54.082673-05	nndz-WkM2eHg3anhndz09	4513	t	\N	6	4	60.00	CC	2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
326196	\N	Betsy	Baker	4571	4334	2025-06-24 19:48:54.082673-05	nndz-WkM2eHhyNzVqQT09	4513	t	\N	2	6	25.00		2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
326197	\N	Laura	Barnett	4571	4334	2025-06-24 19:48:54.082673-05	nndz-WkM2eHhyNzVnUT09	4513	t	\N	1	0	100.00		2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
326198	\N	Ivy	Domont	4571	4334	2025-06-24 19:48:54.082673-05	nndz-WkM2eHhyNzRodz09	4513	t	\N	2	5	28.60		2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
326199	\N	Margalit	Feiger	4571	4334	2025-06-24 19:48:54.082673-05	nndz-WkM2eHhyNzdoUT09	4513	t	\N	1	6	14.30		2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
326200	\N	Kylee	Rudd	4571	4334	2025-06-24 19:48:54.082673-05	nndz-WkM2eHhyNzZoUT09	4513	t	\N	4	3	57.10		2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
326201	\N	Suzanne	Silberman	4571	4334	2025-06-24 19:48:54.082673-05	nndz-WkM2eHhyNzRnZz09	4513	t	\N	3	4	42.90		2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
326202	\N	Lauren	Weiner	4571	4334	2025-06-24 19:48:54.082673-05	nndz-WkM2eHhyNzRqUT09	4513	t	\N	4	3	57.10		2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
326203	\N	Heidi	Sachs	4571	4334	2025-06-24 19:48:54.082673-05	nndz-WkM2eHhyNzRndz09	4513	t	\N	7	4	63.60		2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
326204	\N	Brooke	Kauf	4571	4334	2025-06-24 19:48:54.082673-05	nndz-WkNDL3diajRnZz09	4513	t	\N	0	4	0.00		2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
326205	\N	Stacey	Price	4571	4334	2025-06-24 19:48:54.082673-05	nndz-WkM2eHhyNzRnQT09	4513	t	\N	3	2	60.00		2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
326206	\N	Julie	Lehrman	4572	4334	2025-06-24 19:48:54.082673-05	nndz-WkNDL3dicjRnUT09	4513	t	\N	1	5	16.70	C	2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
326207	\N	Missy	Linn	4572	4334	2025-06-24 19:48:54.082673-05	nndz-WkNDL3dicjRqUT09	4513	t	\N	2	1	66.70	CC	2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
326208	\N	Wendy	Apple	4572	4334	2025-06-24 19:48:54.082673-05	nndz-WkNHNXdyanhoZz09	4513	t	\N	8	1	88.90		2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
326209	\N	Robin	Cohen	4572	4334	2025-06-24 19:48:54.082673-05	nndz-WkNDL3didjVoZz09	4513	t	\N	2	5	28.60		2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
326210	\N	Kim	Colwyn	4572	4334	2025-06-24 19:48:54.082673-05	nndz-WkNHNXc3Yi9odz09	4513	t	\N	8	0	100.00		2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
326211	\N	Juliet	Gray	4572	4334	2025-06-24 19:48:54.082673-05	nndz-WkNHNXc3YjhnZz09	4513	t	\N	0	1	0.00		2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
326212	\N	Hilary	Krasnik	4572	4334	2025-06-24 19:48:54.082673-05	nndz-WkNHNXc3Yi9oUT09	4513	t	\N	0	6	0.00		2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
326213	\N	Dana	Mandell	4572	4334	2025-06-24 19:48:54.082673-05	nndz-WkM2eHlicjZodz09	4513	t	\N	2	4	33.30		2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
326214	\N	Jennifer	Riback	4572	4334	2025-06-24 19:48:54.082673-05	nndz-WkMreHdiN3doQT09	4513	t	\N	1	1	50.00		2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
326215	\N	Carolyn	Spero	4572	4334	2025-06-24 19:48:54.082673-05	nndz-WkM2eHg3ajhnQT09	4513	t	\N	2	6	25.00		2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
326216	\N	Jodi	Taub	4572	4334	2025-06-24 19:48:54.082673-05	nndz-WkNDL3dicjRqQT09	4513	t	\N	3	2	60.00		2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
326217	\N	Lisa	Lord Aronson	4572	4334	2025-06-24 19:48:54.082673-05	nndz-WlNlOXhidjRndz09	4513	t	\N	2	3	40.00		2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
326218	\N	Dawn	Breiter	4572	4334	2025-06-24 19:48:54.082673-05	nndz-WkNDL3diL3hodz09	4513	t	\N	1	2	33.30		2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
326219	\N	Jenny	Dolins	4572	4334	2025-06-24 19:48:54.082673-05	nndz-WkM2eHg3anhnZz09	4513	t	\N	0	0	0.00		2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
326220	\N	Angie	Donenberg	4572	4334	2025-06-24 19:48:54.082673-05	nndz-WkNDOHlMZjhqUT09	4513	t	\N	0	0	0.00		2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
326221	\N	Susie	Morris	4572	4334	2025-06-24 19:48:54.082673-05	nndz-WkM2eHlicjZoZz09	4513	t	\N	1	0	100.00		2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
326222	\N	Jean	Niemi	4599	4334	2025-06-24 19:48:54.082673-05	nndz-WkM2eHg3andoZz09	4513	t	\N	4	3	57.10	C	2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
326223	\N	Rocio	Alvarez	4599	4334	2025-06-24 19:48:54.082673-05	nndz-WkM2eHhyei9qUT09	4513	t	\N	5	3	62.50		2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
326224	\N	Karina	Dehayes	4599	4334	2025-06-24 19:48:54.082673-05	nndz-WkM2eHg3andodz09	4513	t	\N	1	5	16.70		2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
326225	\N	Jessica	Kim	4599	4334	2025-06-24 19:48:54.082673-05	nndz-WkM2eHhyeitoQT09	4513	t	\N	0	1	0.00		2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
326226	\N	Chapin	Konsler	4599	4334	2025-06-24 19:48:54.082673-05	nndz-WlNlN3dMMzlndz09	4513	t	\N	4	1	80.00		2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
326227	\N	Caitlin	Leutwiler Meenan	4599	4334	2025-06-24 19:48:54.082673-05	nndz-WlNhNnlMcnhqUT09	4513	t	\N	4	2	66.70		2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
326228	\N	Ellen	Ley	4599	4334	2025-06-24 19:48:54.082673-05	nndz-WkM2eHhyeitoZz09	4513	t	\N	3	3	50.00		2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
326229	\N	Kathy	Mcarthur	4599	4334	2025-06-24 19:48:54.082673-05	nndz-WkM2eHhyeitnUT09	4513	t	\N	4	1	80.00		2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
326230	\N	Sara	Pickus	4599	4334	2025-06-24 19:48:54.082673-05	nndz-WlNlN3hiajhnUT09	4513	t	\N	1	2	33.30		2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
326231	\N	Gigi	Warren	4599	4334	2025-06-24 19:48:54.082673-05	nndz-WkNHNXdyLy9qUT09	4513	t	\N	3	2	60.00		2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
326232	\N	Sarah	Zaute	4599	4334	2025-06-24 19:48:54.082673-05	nndz-WkMrNnc3di9nUT09	4513	t	\N	1	3	25.00		2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
326233	\N	Amy	Kress Taylor	4599	4334	2025-06-24 19:48:54.082673-05	nndz-WkM2eHhyeitodz09	4513	t	\N	4	4	50.00		2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
326234	\N	Tara	Marazita	4599	4334	2025-06-24 19:48:54.082673-05	nndz-WkMrL3lMejhnQT09	4513	t	\N	5	4	55.60		2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
326235	\N	Susan	Gottlieb	4608	4334	2025-06-24 19:48:54.082673-05	nndz-WkM2eHhyM3doUT09	4513	t	\N	7	1	87.50	C	2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
326236	\N	Leslie	Hinchcliffe	4608	4334	2025-06-24 19:48:54.082673-05	nndz-WkNHNXdMcndnUT09	4513	t	\N	4	4	50.00	CC	2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
326237	\N	Alison	Girard	4608	4334	2025-06-24 19:48:54.082673-05	nndz-WkM2eHlicjloUT09	4513	t	\N	3	0	100.00		2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
326238	\N	Stacy	Mytty	4608	4334	2025-06-24 19:48:54.082673-05	nndz-WkM2eHhMajloQT09	4513	t	\N	4	2	66.70		2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
326239	\N	Holly	Pickering	4608	4334	2025-06-24 19:48:54.082673-05	nndz-WkNHNXdycndnZz09	4513	t	\N	5	0	100.00		2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
326240	\N	Diann	Sheridan	4608	4334	2025-06-24 19:48:54.082673-05	nndz-WkM2eHhyM3dodz09	4513	t	\N	3	5	37.50		2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
326241	\N	Cathy	Tucker	4608	4334	2025-06-24 19:48:54.082673-05	nndz-WkNHNXdMdjVoUT09	4513	t	\N	4	1	80.00		2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
326242	\N	Kathy	McCabe	4608	4334	2025-06-24 19:48:54.082673-05	nndz-WkNHNXdMcndnQT09	4513	t	\N	6	4	60.00		2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
326243	\N	Julie	Moran	4608	4334	2025-06-24 19:48:54.082673-05	nndz-WkNHNXlMLzlnZz09	4513	t	\N	6	4	60.00		2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
326244	\N	Kathy	Ryan	4608	4334	2025-06-24 19:48:54.082673-05	nndz-WkM2eHlicjlnQT09	4513	t	\N	5	10	33.30		2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
326245	\N	Taelor	Fisher	4608	4334	2025-06-24 19:48:54.082673-05	nndz-WlNhNng3cjZoZz09	4513	t	\N	0	3	0.00		2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
326246	\N	Anja	Harvey	4608	4334	2025-06-24 19:48:54.082673-05	nndz-WkNHNXdMZnhndz09	4513	t	\N	0	0	0.00		2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
326247	\N	Lauren	Nisbet	4608	4334	2025-06-24 19:48:54.082673-05	nndz-WkMrL3lMM3doUT09	4513	t	\N	3	2	60.00		2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
326248	\N	Kimberly	Bodden	4610	4334	2025-06-24 19:48:54.082673-05	nndz-WkM2eHhycjloZz09	4513	t	\N	0	2	0.00	C	2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
326249	\N	Jamie	Burns	4610	4334	2025-06-24 19:48:54.082673-05	nndz-WlNlN3g3cjdnZz09	4513	t	\N	0	0	0.00		2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
326250	\N	Morgan	Carr	4610	4334	2025-06-24 19:48:54.082673-05	nndz-WlNlN3dMbndqQT09	4513	t	\N	2	2	50.00		2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
326251	\N	Dina	DeLaurentis	4610	4334	2025-06-24 19:48:54.082673-05	nndz-WlNlN3g3cjdndz09	4513	t	\N	0	0	0.00		2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
326252	\N	Eynav	Epstein	4610	4334	2025-06-24 19:48:54.082673-05	nndz-WlNlN3lidjZoUT09	4513	t	\N	0	7	0.00		2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
326253	\N	Beth	Garino	4610	4334	2025-06-24 19:48:54.082673-05	nndz-WlNlN3g3cjdoZz09	4513	t	\N	0	0	0.00		2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
326254	\N	Andee	Harris	4610	4334	2025-06-24 19:48:54.082673-05	nndz-WlNlN3lidjdqQT09	4513	t	\N	0	0	0.00		2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
326255	\N	Dauwn	Houston	4610	4334	2025-06-24 19:48:54.082673-05	nndz-WlNlOHlibjVqUT09	4513	t	\N	0	3	0.00		2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
326256	\N	Mariana	Ingersoll	4610	4334	2025-06-24 19:48:54.082673-05	nndz-WkM2eHhycjlnQT09	4513	t	\N	0	2	0.00		2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
326257	\N	Kristin	Lordahl	4610	4334	2025-06-24 19:48:54.082673-05	nndz-WlNlL3diMy9qUT09	4513	t	\N	0	3	0.00		2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
326258	\N	Michelle	Motta	4610	4334	2025-06-24 19:48:54.082673-05	nndz-WlNlN3g3cjdodz09	4513	t	\N	0	4	0.00		2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
326259	\N	Diann	Nails	4610	4334	2025-06-24 19:48:54.082673-05	nndz-WlNlN3g3cjRqUT09	4513	t	\N	0	2	0.00		2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
326260	\N	Kristin	Pillsbury	4610	4334	2025-06-24 19:48:54.082673-05	nndz-WlNlN3g3cjRqQT09	4513	t	\N	0	1	0.00		2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
326261	\N	Meryl	Rosen	4610	4334	2025-06-24 19:48:54.082673-05	nndz-WkNHNXc3ajVoQT09	4513	t	\N	0	0	0.00		2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
326262	\N	Lisa	Stam	4610	4334	2025-06-24 19:48:54.082673-05	nndz-WlNlOXdiNzVqUT09	4513	t	\N	0	0	0.00		2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
326263	\N	Vanessa	Summer	4610	4334	2025-06-24 19:48:54.082673-05	nndz-WlNlL3hydndoQT09	4513	t	\N	0	0	0.00		2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
326264	\N	Brigette	Wilkins	4610	4334	2025-06-24 19:48:54.082673-05	nndz-WlNlL3dyejZndz09	4513	t	\N	0	4	0.00		2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
326265	\N	Krista	Blazek Hogarth	4610	4334	2025-06-24 19:48:54.082673-05	nndz-WkM2eHhycjlodz09	4513	t	\N	4	3	57.10		2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
326266	\N	Sarah	Jamieson	4610	4334	2025-06-24 19:48:54.082673-05	nndz-WlNlN3g3cjdoUT09	4513	t	\N	3	1	75.00		2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
326267	\N	Meghan	Zuercher	4611	4334	2025-06-24 19:48:54.082673-05	nndz-WkM2eHg3aitnUT09	4513	t	\N	5	3	62.50	C	2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
326268	\N	Sharon	Ashley	4611	4334	2025-06-24 19:48:54.082673-05	nndz-WkNDL3didjZnZz09	4513	t	\N	1	3	25.00		2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
326269	\N	Lauren	Bozzelli	4611	4334	2025-06-24 19:48:54.082673-05	nndz-WkNHN3didjhnUT09	4513	t	\N	4	3	57.10		2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
326270	\N	Carolyn	Collins	4611	4334	2025-06-24 19:48:54.082673-05	nndz-WkMrL3lMNzZnUT09	4513	t	\N	4	1	80.00		2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
326271	\N	Maggie	Hammond	4611	4334	2025-06-24 19:48:54.082673-05	nndz-WkNHNXdMMzZnQT09	4513	t	\N	6	0	100.00		2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
326272	\N	Jackie	Kramer	4611	4334	2025-06-24 19:48:54.082673-05	nndz-WkNDL3diM3dnZz09	4513	t	\N	1	0	100.00		2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
326273	\N	Donna	Placio	4611	4334	2025-06-24 19:48:54.082673-05	nndz-WkNDL3didjZndz09	4513	t	\N	4	1	80.00		2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
326274	\N	Tracy	Power	4611	4334	2025-06-24 19:48:54.082673-05	nndz-WkM2eHhycjhoZz09	4513	t	\N	2	6	25.00		2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
326275	\N	Megan	Anderson	4611	4334	2025-06-24 19:48:54.082673-05	nndz-WkNDL3didjZnUT09	4513	t	\N	0	10	0.00		2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
326276	\N	Kirsten	Kenny	4611	4334	2025-06-24 19:48:54.082673-05	nndz-WkNDL3dicjVnQT09	4513	t	\N	1	8	11.10		2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
326277	\N	Kathleen	Bauer	4611	4334	2025-06-24 19:48:54.082673-05	nndz-WkMrNnc3ajhnZz09	4513	t	\N	0	0	0.00		2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
326278	\N	Laura	Selby	4611	4334	2025-06-24 19:48:54.082673-05	nndz-WkNHNXdMMzlodz09	4513	t	\N	0	1	0.00		2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
326279	\N	Karie	Smith	4611	4334	2025-06-24 19:48:54.082673-05	nndz-WlNlOXliYjhoZz09	4513	t	\N	0	0	0.00		2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
326280	\N	Jordan	Daul	4611	4334	2025-06-24 19:48:54.082673-05	nndz-WkM2eHhycjhnQT09	4513	t	\N	1	4	20.00		2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
326281	\N	Linda	Felter	4611	4334	2025-06-24 19:48:54.082673-05	nndz-WkM2d3c3djVoZz09	4513	t	\N	0	6	0.00		2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
326282	\N	Taylor	Kehoe	4611	4334	2025-06-24 19:48:54.082673-05	nndz-WkMrL3lMLzlodz09	4513	t	\N	3	4	42.90		2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
326283	\N	Claire	Manning	4611	4334	2025-06-24 19:48:54.082673-05	nndz-WkMreHhMN3doUT09	4513	t	\N	6	1	85.70		2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
326284	\N	Clare	Martin	4611	4334	2025-06-24 19:48:54.082673-05	nndz-WkM2eHhycjhqUT09	4513	t	\N	2	5	28.60		2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
326285	\N	AMY	MCCANN	4611	4334	2025-06-24 19:48:54.082673-05	nndz-WkMrK3dybndnUT09	4513	t	\N	6	5	54.50		2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
326286	\N	Stephanie	Morrisroe	4611	4334	2025-06-24 19:48:54.082673-05	nndz-WkM2eHhyci9oUT09	4513	t	\N	2	4	33.30		2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
326287	\N	Maria	Schafer	4611	4334	2025-06-24 19:48:54.082673-05	nndz-WkNDL3diM3dqUT09	4513	t	\N	1	1	50.00		2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
326288	\N	Meghan	Shanahan	4611	4334	2025-06-24 19:48:54.082673-05	nndz-WkM2d3c3djVqQT09	4513	t	\N	7	1	87.50		2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
326289	\N	Dana	Trumbull	4611	4334	2025-06-24 19:48:54.082673-05	nndz-WkM2d3c3djRoUT09	4513	t	\N	5	2	71.40		2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
326290	\N	Lisa	Foley	4635	4334	2025-06-24 19:48:54.082673-05	nndz-WkNDL3diditqQT09	4513	t	\N	2	4	33.30	C	2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
326291	\N	Courtney	Mathy	4635	4334	2025-06-24 19:48:54.082673-05	nndz-WkNDL3didjhnZz09	4513	t	\N	1	2	33.30	CC	2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
326292	\N	Jen	Ali	4635	4334	2025-06-24 19:48:54.082673-05	nndz-WkNDL3didjhndz09	4513	t	\N	0	0	0.00		2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
326293	\N	Lara	Beanblossom	4635	4334	2025-06-24 19:48:54.082673-05	nndz-WkNDL3diMzhndz09	4513	t	\N	2	1	66.70		2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
326294	\N	Natalie	Daverman	4635	4334	2025-06-24 19:48:54.082673-05	nndz-WkNDL3diajRoZz09	4513	t	\N	1	5	16.70		2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
326295	\N	Cary	Gerlinger	4635	4334	2025-06-24 19:48:54.082673-05	nndz-WkMrK3diejZodz09	4513	t	\N	2	3	40.00		2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
326296	\N	Sarah	Graham	4635	4334	2025-06-24 19:48:54.082673-05	nndz-WkM2eHg3ajhoUT09	4513	t	\N	2	1	66.70		2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
326297	\N	Mary	Beth Harlin	4635	4334	2025-06-24 19:48:54.082673-05	nndz-WkM2eHhyajdoUT09	4513	t	\N	0	4	0.00		2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
326298	\N	Holly	Meacham	4635	4334	2025-06-24 19:48:54.082673-05	nndz-WkM2eHhyajdnUT09	4513	t	\N	0	6	0.00		2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
326299	\N	Cara	Snyder	4635	4334	2025-06-24 19:48:54.082673-05	nndz-WkNDL3diajRoQT09	4513	t	\N	1	2	33.30		2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
326300	\N	Stephanie	Wheat	4635	4334	2025-06-24 19:48:54.082673-05	nndz-WkM2eHhyajdnZz09	4513	t	\N	1	4	20.00		2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
326301	\N	Margaret	Chaffee	4635	4334	2025-06-24 19:48:54.082673-05	nndz-WkMrK3c3YjVnQT09	4513	t	\N	3	4	42.90		2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
326302	\N	Melissa	David	4635	4334	2025-06-24 19:48:54.082673-05	nndz-WkNDL3diN3hqUT09	4513	t	\N	3	2	60.00		2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
326303	\N	Maggie	Buckman	4635	4334	2025-06-24 19:48:54.082673-05	nndz-WlNhNndMM3hqQT09	4513	t	\N	5	5	50.00		2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
326304	\N	Laura	Margolis	4635	4334	2025-06-24 19:48:54.082673-05	nndz-WkMrK3diZndodz09	4513	t	\N	6	3	66.70		2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
326305	\N	Kate	Neal	4635	4334	2025-06-24 19:48:54.082673-05	nndz-WkNDL3dicjZoQT09	4513	t	\N	1	0	100.00		2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
326306	\N	Jill	Beckstedt	4635	4334	2025-06-24 19:48:54.082673-05	nndz-WkNDL3diajRodz09	4513	t	\N	1	2	33.30		2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
326307	\N	Caitlin	Eck	4635	4334	2025-06-24 19:48:54.082673-05	nndz-WkMrL3lMbi9nUT09	4513	t	\N	1	6	14.30		2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
326308	\N	Jennifer	Mackey	4635	4334	2025-06-24 19:48:54.082673-05	nndz-WkM2eHhyajdodz09	4513	t	\N	4	3	57.10		2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
326309	\N	Karen	Walker	4635	4334	2025-06-24 19:48:54.082673-05	nndz-WkM2d3dMYjhqUT09	4513	t	\N	6	5	54.50		2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
326310	\N	Jayme	Marino	4637	4334	2025-06-24 19:48:54.082673-05	nndz-WkM2eHhybjRoZz09	4513	t	\N	11	4	73.30	C	2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
326311	\N	Paige	Wenk	4637	4334	2025-06-24 19:48:54.082673-05	nndz-WkNDeHdiNzRoUT09	4513	t	\N	1	2	33.30	CC	2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
326312	\N	Jessica	Brosche	4637	4334	2025-06-24 19:48:54.082673-05	nndz-WkNDL3dicjhoQT09	4513	t	\N	0	0	0.00		2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
326313	\N	Ashley	Demakis	4637	4334	2025-06-24 19:48:54.082673-05	nndz-WkM2eHg3bjZoZz09	4513	t	\N	6	3	66.70		2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
326314	\N	Abbey	Driscoll	4637	4334	2025-06-24 19:48:54.082673-05	nndz-WlNlN3c3ejlnZz09	4513	t	\N	7	1	87.50		2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
326315	\N	Val	King	4637	4334	2025-06-24 19:48:54.082673-05	nndz-WkNDeHdiNzZoQT09	4513	t	\N	0	0	0.00		2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
326316	\N	Sara	Kirmser	4637	4334	2025-06-24 19:48:54.082673-05	nndz-WkMrNndMLzZndz09	4513	t	\N	4	4	50.00		2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
326317	\N	Heather	Mcdevitt	4637	4334	2025-06-24 19:48:54.082673-05	nndz-WkM2eHhybjRnUT09	4513	t	\N	11	2	84.60		2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
326318	\N	Elizabeth	Silvia	4637	4334	2025-06-24 19:48:54.082673-05	nndz-WkMrK3dibjZoZz09	4513	t	\N	8	7	53.30		2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
326319	\N	Megan	Waite	4637	4334	2025-06-24 19:48:54.082673-05	nndz-WkM2eHhybjRnQT09	4513	t	\N	3	2	60.00		2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
326320	\N	Jennifer	Tucker	4637	4334	2025-06-24 19:48:54.082673-05	nndz-WkM2eHg3bjZqUT09	4513	t	\N	12	2	85.70		2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
326321	\N	Jennifer	Mcginn	4637	4334	2025-06-24 19:48:54.082673-05	nndz-WkM2eHhybjVoQT09	4513	t	\N	4	4	50.00		2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
326322	\N	Lindsay	Salsbery	4637	4334	2025-06-24 19:48:54.082673-05	nndz-WlNlL3hiLzlqUT09	4513	t	\N	0	2	0.00		2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
326323	\N	Britt	Vranek	4637	4334	2025-06-24 19:48:54.082673-05	nndz-WkMrK3dianhndz09	4513	t	\N	4	4	50.00		2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
326324	\N	Shannon	Bernard	4637	4334	2025-06-24 19:48:54.082673-05	nndz-WkM2eHhyandqUT09	4513	t	\N	4	3	57.10		2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
326325	\N	Sarah	Cohen	4637	4334	2025-06-24 19:48:54.082673-05	nndz-WkM2eHhyandqQT09	4513	t	\N	6	2	75.00		2025-06-24 19:48:54.082673-05	0	0	0	0.00	\N
326326	\N	Kate	Fisher	4637	4334	2025-06-24 19:48:54.333136-05	nndz-WkM2eHhybjRoUT09	4513	t	\N	2	6	25.00		2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
326327	\N	Kathryn	McGowan	4637	4334	2025-06-24 19:48:54.333136-05	nndz-WkMrK3hyM3hodz09	4513	t	\N	9	2	81.80		2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
326328	\N	Renee	Zipprich	4640	4334	2025-06-24 19:48:54.333136-05	nndz-WkNDK3dybjlnQT09	4513	t	\N	1	3	25.00	C	2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
326329	\N	Megan	Butler	4640	4334	2025-06-24 19:48:54.333136-05	nndz-WkM2eHliLzRoZz09	4513	t	\N	3	2	60.00	CC	2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
326330	\N	Lisa	Alternbernd Hagerty	4640	4334	2025-06-24 19:48:54.333136-05	nndz-WkNHNXc3ci9oZz09	4513	t	\N	3	4	42.90		2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
326331	\N	Jami	Brown	4640	4334	2025-06-24 19:48:54.333136-05	nndz-WkNDL3dicnhoZz09	4513	t	\N	1	5	16.70		2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
326332	\N	Carolyn	Gilbert	4640	4334	2025-06-24 19:48:54.333136-05	nndz-WkNDL3dicitqUT09	4513	t	\N	1	3	25.00		2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
326333	\N	Courtney	Jack	4640	4334	2025-06-24 19:48:54.333136-05	nndz-WkNDL3diejlnQT09	4513	t	\N	0	3	0.00		2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
326334	\N	Courtney	McConnell	4640	4334	2025-06-24 19:48:54.333136-05	nndz-WkM2eHg3ajhodz09	4513	t	\N	4	3	57.10		2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
326335	\N	Maegan	Oneal	4640	4334	2025-06-24 19:48:54.333136-05	nndz-WkM2eHhyZjdnQT09	4513	t	\N	4	4	50.00		2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
326336	\N	Nora	Shea	4640	4334	2025-06-24 19:48:54.333136-05	nndz-WkNDL3didi9nUT09	4513	t	\N	3	1	75.00		2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
326337	\N	Anne	Snyder	4640	4334	2025-06-24 19:48:54.333136-05	nndz-WkNDL3dicndnQT09	4513	t	\N	1	4	20.00		2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
326338	\N	Christina	Glisson	4640	4334	2025-06-24 19:48:54.333136-05	nndz-WkM2eHhyZjdnUT09	4513	t	\N	5	3	62.50		2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
326339	\N	Mary	White	4640	4334	2025-06-24 19:48:54.333136-05	nndz-WkM2eHhyZitnUT09	4513	t	\N	3	1	75.00		2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
326340	\N	Amy	Chung	4640	4334	2025-06-24 19:48:54.333136-05	nndz-WkM2eHhyZjdoZz09	4513	t	\N	0	1	0.00		2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
326341	\N	Mary	Jo Lestingi	4640	4334	2025-06-24 19:48:54.333136-05	nndz-WkM2eHg3ejZodz09	4513	t	\N	2	1	66.70		2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
326342	\N	Janet	Scholl	4640	4334	2025-06-24 19:48:54.333136-05	nndz-WkM2eHhyZjZnUT09	4513	t	\N	0	0	0.00		2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
326343	\N	Blakely	Marx	4646	4334	2025-06-24 19:48:54.333136-05	nndz-WkMrK3dMNy9ndz09	4513	t	\N	7	1	87.50	C	2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
326344	\N	Alison	Marino	4646	4334	2025-06-24 19:48:54.333136-05	nndz-WkMrK3diM3hodz09	4513	t	\N	10	3	76.90	CC	2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
326345	\N	Christine	Adams	4646	4334	2025-06-24 19:48:54.333136-05	nndz-WkM2d3hiditqQT09	4513	t	\N	6	4	60.00		2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
326346	\N	Dana	Cahan	4646	4334	2025-06-24 19:48:54.333136-05	nndz-WkMrK3diYjRodz09	4513	t	\N	6	1	85.70		2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
326347	\N	Lynn	Hanley	4646	4334	2025-06-24 19:48:54.333136-05	nndz-WkMrK3diMy9ndz09	4513	t	\N	4	3	57.10		2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
326348	\N	Stacie	Harrison	4646	4334	2025-06-24 19:48:54.333136-05	nndz-WkM2eHg3ai9nUT09	4513	t	\N	4	3	57.10		2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
326349	\N	Erin	Humphrey	4646	4334	2025-06-24 19:48:54.333136-05	nndz-WkMrK3hMdnhqUT09	4513	t	\N	6	2	75.00		2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
326350	\N	Debbie	Kelly	4646	4334	2025-06-24 19:48:54.333136-05	nndz-WkNHNXdyLy9oQT09	4513	t	\N	3	2	60.00		2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
326351	\N	Cathy	Melidones	4646	4334	2025-06-24 19:48:54.333136-05	nndz-WkMrOHhidnhqQT09	4513	t	\N	0	0	0.00		2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
326352	\N	Christine	Morse	4646	4334	2025-06-24 19:48:54.333136-05	nndz-WkM2eHhyejloQT09	4513	t	\N	1	5	16.70		2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
326353	\N	Cristina	Aliagas	4646	4334	2025-06-24 19:48:54.333136-05	nndz-WkM2d3hidnhoZz09	4513	t	\N	8	2	80.00		2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
326354	\N	Susana	Castella	4646	4334	2025-06-24 19:48:54.333136-05	nndz-WkM2d3hidnhoUT09	4513	t	\N	4	1	80.00		2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
326355	\N	Polly	Richter	4646	4334	2025-06-24 19:48:54.333136-05	nndz-WkM2eHliLy9qUT09	4513	t	\N	1	5	16.70		2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
326356	\N	Melissa	Buckley	4567	4335	2025-06-24 19:48:54.333136-05	nndz-WkNDeHdiN3hoZz09	4513	t	\N	3	6	33.30	C	2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
326357	\N	Susan	Nelsen	4567	4335	2025-06-24 19:48:54.333136-05	nndz-WkNDeHdiNytqUT09	4513	t	\N	0	6	0.00	CC	2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
326358	\N	Jane	Buchel	4567	4335	2025-06-24 19:48:54.333136-05	nndz-WkNHNXdyLzdoZz09	4513	t	\N	3	6	33.30		2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
326359	\N	Lynda	Coffman	4567	4335	2025-06-24 19:48:54.333136-05	nndz-WkNHNXdyLzdoQT09	4513	t	\N	1	2	33.30		2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
326360	\N	Kristin	Cox	4567	4335	2025-06-24 19:48:54.333136-05	nndz-WkNHNXdyLzdndz09	4513	t	\N	1	4	20.00		2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
326361	\N	Alison	Duke	4567	4335	2025-06-24 19:48:54.333136-05	nndz-WkM2eHg3Zi9nQT09	4513	t	\N	3	0	100.00		2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
326362	\N	Gayle	Gianopulos	4567	4335	2025-06-24 19:48:54.333136-05	nndz-WkNHNXdyLzdnZz09	4513	t	\N	1	3	25.00		2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
326363	\N	Tracy	Karambelas	4567	4335	2025-06-24 19:48:54.333136-05	nndz-WkMrK3dyZitoQT09	4513	t	\N	0	4	0.00		2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
326364	\N	Hillary	Lockefeer	4567	4335	2025-06-24 19:48:54.333136-05	nndz-WkNHNXdyLzdnUT09	4513	t	\N	0	0	0.00		2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
326365	\N	Tiffany	Marshall	4567	4335	2025-06-24 19:48:54.333136-05	nndz-WkM2eHg3Zi9qUT09	4513	t	\N	2	4	33.30		2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
326366	\N	Ashlie	McDonnell	4567	4335	2025-06-24 19:48:54.333136-05	nndz-WkMrN3lidjdnQT09	4513	t	\N	5	1	83.30		2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
326367	\N	Lisa	Ploder	4567	4335	2025-06-24 19:48:54.333136-05	nndz-WkNHNXdyLzdoUT09	4513	t	\N	0	4	0.00		2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
326368	\N	Lanisa	Tricoci Scurto	4567	4335	2025-06-24 19:48:54.333136-05	nndz-WkMrK3dMMzZodz09	4513	t	\N	4	3	57.10		2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
326369	\N	Britini	Wilkens	4567	4335	2025-06-24 19:48:54.333136-05	nndz-WkMrK3hMMzRndz09	4513	t	\N	3	1	75.00		2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
326370	\N	Hilary	Atamian	4567	4335	2025-06-24 19:48:54.333136-05	nndz-WlNlNnlidjhndz09	4513	t	\N	1	2	33.30		2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
326371	\N	Lara	Berry	4567	4335	2025-06-24 19:48:54.333136-05	nndz-WkM2eHg3Zi9nUT09	4513	t	\N	0	2	0.00		2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
326372	\N	Laura	Fitch	4567	4335	2025-06-24 19:48:54.333136-05	nndz-WkM2eHg3Zi9ndz09	4513	t	\N	0	5	0.00		2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
326373	\N	Peggy	Hirsch	4567	4335	2025-06-24 19:48:54.333136-05	nndz-WkNDL3diLzlqQT09	4513	t	\N	0	0	0.00		2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
326374	\N	Linda	Hovde	4567	4335	2025-06-24 19:48:54.333136-05	nndz-WkM2eHg3Zi9nZz09	4513	t	\N	0	0	0.00		2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
326375	\N	Gina	Koertner	4567	4335	2025-06-24 19:48:54.333136-05	nndz-WkMrK3c3N3dndz09	4513	t	\N	0	2	0.00		2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
326376	\N	Meghan	Van Daele	4567	4335	2025-06-24 19:48:54.333136-05	nndz-WkMrK3diZndnQT09	4513	t	\N	0	0	0.00		2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
326377	\N	Debra	Dickson	4569	4336	2025-06-24 19:48:54.333136-05	nndz-WkM2eHhMajlnUT09	4513	t	\N	0	1	0.00	C	2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
326378	\N	Anne	Collins	4569	4336	2025-06-24 19:48:54.333136-05	nndz-WkM2eHhMajloZz09	4513	t	\N	2	1	66.70	CC	2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
326379	\N	Ellen	Adler	4569	4336	2025-06-24 19:48:54.333136-05	nndz-WkM2eHg3ZndoUT09	4513	t	\N	6	3	66.70		2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
326380	\N	Andee	Blomquist	4569	4336	2025-06-24 19:48:54.333136-05	nndz-WkM2eHg3ZndoZz09	4513	t	\N	4	4	50.00		2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
326381	\N	Jenny	Bulgarelli	4569	4336	2025-06-24 19:48:54.333136-05	nndz-WkM2eHg3ZndnUT09	4513	t	\N	0	5	0.00		2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
326382	\N	Mary	Dale	4569	4336	2025-06-24 19:48:54.333136-05	nndz-WkM2eHg3ZndnQT09	4513	t	\N	3	3	50.00		2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
326383	\N	Holly	Husby	4569	4336	2025-06-24 19:48:54.333136-05	nndz-WkM2eHg3ZndnZz09	4513	t	\N	0	4	0.00		2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
326384	\N	Nicole	Jankowski	4569	4336	2025-06-24 19:48:54.333136-05	nndz-WkM2eHg3ZndqUT09	4513	t	\N	5	2	71.40		2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
326385	\N	Ann	Messer	4569	4336	2025-06-24 19:48:54.333136-05	nndz-WkM2eHhyNzVoUT09	4513	t	\N	5	1	83.30		2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
326386	\N	Lesley	Olson	4569	4336	2025-06-24 19:48:54.333136-05	nndz-WkM2eHhyNzVodz09	4513	t	\N	7	3	70.00		2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
326387	\N	Erin	Shechtman	4569	4336	2025-06-24 19:48:54.333136-05	nndz-WkM2eHhyNzVoZz09	4513	t	\N	4	2	66.70		2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
326388	\N	Molly	Archibald	4569	4336	2025-06-24 19:48:54.333136-05	nndz-WlNlL3hicjloUT09	4513	t	\N	1	2	33.30		2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
326389	\N	Jackie	Babel	4569	4336	2025-06-24 19:48:54.333136-05	nndz-WlNlOXdybjlnZz09	4513	t	\N	0	0	0.00		2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
326390	\N	Michelle	Blues	4569	4336	2025-06-24 19:48:54.333136-05	nndz-WlNlOXdybjlqUT09	4513	t	\N	1	0	100.00		2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
326391	\N	Claire	Hamilton	4569	4336	2025-06-24 19:48:54.333136-05	nndz-WkMrNnc3ajlndz09	4513	t	\N	0	1	0.00		2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
326392	\N	Krissy	Lohmeyer	4569	4336	2025-06-24 19:48:54.333136-05	nndz-WkM2eHg3ZndqQT09	4513	t	\N	0	1	0.00		2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
326393	\N	Karen	McGee	4569	4336	2025-06-24 19:48:54.333136-05	nndz-WkMrK3hMZjdqQT09	4513	t	\N	0	1	0.00		2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
326394	\N	Angie	Schwartz	4569	4336	2025-06-24 19:48:54.333136-05	nndz-WkMrN3hMZjRoUT09	4513	t	\N	0	1	0.00		2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
326395	\N	Shelley	Szela	4569	4336	2025-06-24 19:48:54.333136-05	nndz-WkM2d3dMdi9nZz09	4513	t	\N	0	0	0.00		2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
326396	\N	Mary	Tarpey	4569	4337	2025-06-24 19:48:54.333136-05	nndz-WkM2d3g3djRndz09	4513	t	\N	7	0	100.00	C	2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
326397	\N	Sara	Ray	4569	4337	2025-06-24 19:48:54.333136-05	nndz-WkMrK3g3djlndz09	4513	t	\N	4	0	100.00	CC	2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
326398	\N	Elana	Anastasiou	4569	4337	2025-06-24 19:48:54.333136-05	nndz-WkM2eHg3ZndoQT09	4513	t	\N	0	0	0.00		2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
326399	\N	Christine	Birch	4569	4337	2025-06-24 19:48:54.333136-05	nndz-WkMrL3lMZjRodz09	4513	t	\N	4	0	100.00		2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
326400	\N	Kelly	Carden	4569	4337	2025-06-24 19:48:54.333136-05	nndz-WkM2d3dyLzVodz09	4513	t	\N	7	1	87.50		2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
326401	\N	Catherine	Lange	4569	4337	2025-06-24 19:48:54.333136-05	nndz-WkM2d3dMditoUT09	4513	t	\N	4	0	100.00		2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
326402	\N	Christine	Mickey	4569	4337	2025-06-24 19:48:54.333136-05	nndz-WkM2eHhyNzVoQT09	4513	t	\N	4	0	100.00		2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
326403	\N	Jenn	Newman	4569	4337	2025-06-24 19:48:54.333136-05	nndz-WkMrK3diZjVoZz09	4513	t	\N	5	0	100.00		2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
326404	\N	Melissa	Nisbet	4569	4337	2025-06-24 19:48:54.333136-05	nndz-WlNhL3dyejRoUT09	4513	t	\N	6	0	100.00		2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
326405	\N	Jenna	Shields	4569	4337	2025-06-24 19:48:54.333136-05	nndz-WkMrL3lMZjlqQT09	4513	t	\N	3	0	100.00		2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
326406	\N	Colleen	Stevanovich	4569	4337	2025-06-24 19:48:54.333136-05	nndz-WkMrK3lMMytoUT09	4513	t	\N	0	0	0.00		2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
326407	\N	Betsy	Thalheimer	4569	4337	2025-06-24 19:48:54.333136-05	nndz-WkM2d3dyLzVnUT09	4513	t	\N	5	2	71.40		2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
326408	\N	Katie	Karam	4569	4337	2025-06-24 19:48:54.333136-05	nndz-WkMreHhML3hqQT09	4513	t	\N	1	3	25.00		2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
326409	\N	Tiffany	Seely-Brown	4569	4337	2025-06-24 19:48:54.333136-05	nndz-WkMrK3hMbjlqUT09	4513	t	\N	5	1	83.30		2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
326410	\N	Simone	Zorzy	4569	4337	2025-06-24 19:48:54.333136-05	nndz-WkMrK3hMajlqQT09	4513	t	\N	8	2	80.00		2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
326411	\N	Molly	Archibald	4569	4337	2025-06-24 19:48:54.333136-05	nndz-WlNlL3hicjloUT09	4513	t	\N	1	2	33.30		2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
326412	\N	Jackie	Babel	4569	4337	2025-06-24 19:48:54.333136-05	nndz-WlNlOXdybjlnZz09	4513	t	\N	0	0	0.00		2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
326413	\N	Michelle	Blues	4569	4337	2025-06-24 19:48:54.333136-05	nndz-WlNlOXdybjlqUT09	4513	t	\N	1	0	100.00		2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
326414	\N	Brooke	Haller	4569	4337	2025-06-24 19:48:54.333136-05	nndz-WkM2eHg3Zndndz09	4513	t	\N	1	0	100.00		2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
326415	\N	Claire	Hamilton	4569	4337	2025-06-24 19:48:54.333136-05	nndz-WkMrNnc3ajlndz09	4513	t	\N	0	1	0.00		2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
326416	\N	Krissy	Lohmeyer	4569	4337	2025-06-24 19:48:54.333136-05	nndz-WkM2eHg3ZndqQT09	4513	t	\N	0	1	0.00		2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
326417	\N	Karen	McGee	4569	4337	2025-06-24 19:48:54.333136-05	nndz-WkMrK3hMZjdqQT09	4513	t	\N	0	1	0.00		2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
326418	\N	Angie	Schwartz	4569	4337	2025-06-24 19:48:54.333136-05	nndz-WkMrN3hMZjRoUT09	4513	t	\N	0	1	0.00		2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
326419	\N	Shelley	Szela	4569	4337	2025-06-24 19:48:54.333136-05	nndz-WkM2d3dMdi9nZz09	4513	t	\N	0	0	0.00		2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
326420	\N	Agnes	Tomasian	4569	4337	2025-06-24 19:48:54.333136-05	nndz-WkM2d3dMdi9qUT09	4513	t	\N	1	0	100.00		2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
326421	\N	Michelle	Whitworth	4579	4335	2025-06-24 19:48:54.333136-05	nndz-WkMrK3dyLzhqUT09	4513	t	\N	4	1	80.00	C	2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
326422	\N	Michelle	Zimmerman	4579	4335	2025-06-24 19:48:54.333136-05	nndz-WkM2eHhyNy9qUT09	4513	t	\N	0	0	0.00	CC	2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
326423	\N	Nancy	Ackerman	4579	4335	2025-06-24 19:48:54.333136-05	nndz-WkNDOHlMYi9qQT09	4513	t	\N	4	1	80.00		2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
326424	\N	Christine	Bridger	4579	4335	2025-06-24 19:48:54.333136-05	nndz-WkM2eHg3anhqUT09	4513	t	\N	5	1	83.30		2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
326425	\N	Cathleen	Dooley	4579	4335	2025-06-24 19:48:54.333136-05	nndz-WkMrK3dyL3hnUT09	4513	t	\N	3	1	75.00		2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
326426	\N	Maureen	Gribble	4579	4335	2025-06-24 19:48:54.333136-05	nndz-WkM2eHhyNy9oUT09	4513	t	\N	3	2	60.00		2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
326427	\N	Karen	McKeon	4579	4335	2025-06-24 19:48:54.333136-05	nndz-WkNDL3didjRoUT09	4513	t	\N	3	2	60.00		2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
326428	\N	Anne	Sidrys	4579	4335	2025-06-24 19:48:54.333136-05	nndz-WkMrK3dyLzhnZz09	4513	t	\N	4	2	66.70		2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
326429	\N	Liz	Barnett	4579	4335	2025-06-24 19:48:54.333136-05	nndz-WkMrK3diei9oZz09	4513	t	\N	5	3	62.50		2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
326430	\N	Larissa	Kins	4579	4335	2025-06-24 19:48:54.333136-05	nndz-WkMrK3dyLzhnQT09	4513	t	\N	3	2	60.00		2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
326431	\N	Kelly	Monahan	4579	4335	2025-06-24 19:48:54.333136-05	nndz-WkMrL3lMandnQT09	4513	t	\N	6	1	85.70		2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
326432	\N	Anne	Murdoch	4579	4335	2025-06-24 19:48:54.333136-05	nndz-WkM2eHhyNzhnUT09	4513	t	\N	6	3	66.70		2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
326433	\N	Margaret	LeFevour	4579	4335	2025-06-24 19:48:54.333136-05	nndz-WkMrK3diZitoUT09	4513	t	\N	2	4	33.30		2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
326434	\N	Solita	Murphy	4579	4335	2025-06-24 19:48:54.333136-05	nndz-WkMrNndiZjhqQT09	4513	t	\N	0	0	0.00		2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
326435	\N	Libby	Carlson	4579	4335	2025-06-24 19:48:54.333136-05	nndz-WkMrK3dyLy9oZz09	4513	t	\N	2	3	40.00		2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
326436	\N	Heather	Shaffer	4579	4335	2025-06-24 19:48:54.333136-05	nndz-WlNlN3diNzhoUT09	4513	t	\N	3	4	42.90		2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
326437	\N	Liz	Aktar	4580	4335	2025-06-24 19:48:54.333136-05	nndz-WlNlOXdyMy9nUT09	4513	t	\N	2	3	40.00	C	2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
326438	\N	Nancy	Blankstein	4580	4335	2025-06-24 19:48:54.333136-05	nndz-WkNDL3dici9qQT09	4513	t	\N	1	4	20.00		2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
326439	\N	Katie	Dunlop	4580	4335	2025-06-24 19:48:54.333136-05	nndz-WkM2eHhyLzZoUT09	4513	t	\N	4	3	57.10		2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
326440	\N	Jennifer	Rubenstein	4580	4335	2025-06-24 19:48:54.333136-05	nndz-WkM2eHhyLzZndz09	4513	t	\N	0	0	0.00		2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
326441	\N	Alison	Sierens	4580	4335	2025-06-24 19:48:54.333136-05	nndz-WkNDeHdiNy9nUT09	4513	t	\N	0	0	0.00		2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
326442	\N	Pam	Soper	4580	4335	2025-06-24 19:48:54.333136-05	nndz-WkM2eHhyLzdnUT09	4513	t	\N	4	2	66.70		2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
326443	\N	Robin	Ekenberg	4580	4335	2025-06-24 19:48:54.333136-05	nndz-WkNDL3dicitoUT09	4513	t	\N	1	8	11.10		2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
326444	\N	Erin	Lawler	4580	4335	2025-06-24 19:48:54.333136-05	nndz-WkM2eHhyLzlqQT09	4513	t	\N	6	2	75.00		2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
326445	\N	Leah	Mayer	4580	4335	2025-06-24 19:48:54.333136-05	nndz-WkM2eHhyLzZoZz09	4513	t	\N	3	5	37.50		2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
326446	\N	Maro	Zrike	4580	4335	2025-06-24 19:48:54.333136-05	nndz-WkM2eHhyLy9oZz09	4513	t	\N	6	3	66.70		2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
326447	\N	Katie	Alland	4580	4335	2025-06-24 19:48:54.333136-05	nndz-WlNlOHlibjZqUT09	4513	t	\N	4	4	50.00		2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
326448	\N	Rae	Gruetzmacher	4580	4335	2025-06-24 19:48:54.333136-05	nndz-WlNlN3hiYjloZz09	4513	t	\N	6	7	46.20		2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
326449	\N	Mary	Clare Kadison	4580	4335	2025-06-24 19:48:54.333136-05	nndz-WlNhNnhiLzloQT09	4513	t	\N	8	2	80.00		2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
326450	\N	Kacey	Koessl	4580	4335	2025-06-24 19:48:54.333136-05	nndz-WkMreHhyejhnQT09	4513	t	\N	9	0	100.00		2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
326451	\N	Ann	Phillips	4580	4335	2025-06-24 19:48:54.333136-05	nndz-WlNlNnliai9ndz09	4513	t	\N	1	1	50.00		2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
326452	\N	Candice	Pelser	4600	4335	2025-06-24 19:48:54.333136-05	nndz-WkM2eHhyMzVndz09	4513	t	\N	0	0	0.00	C	2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
326453	\N	Janel	Brown	4600	4335	2025-06-24 19:48:54.333136-05	nndz-WkM2eHhyMzhnZz09	4513	t	\N	0	7	0.00		2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
326454	\N	Michelle	Dooley	4600	4335	2025-06-24 19:48:54.333136-05	nndz-WlNlN3hiendnQT09	4513	t	\N	1	7	12.50		2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
326455	\N	Carolina	Garcia-Leahy	4600	4335	2025-06-24 19:48:54.333136-05	nndz-WkM2eHhyMzVoQT09	4513	t	\N	1	7	12.50		2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
326456	\N	Sara	Lohr	4600	4335	2025-06-24 19:48:54.333136-05	nndz-WkM2eHhyMzVnUT09	4513	t	\N	0	6	0.00		2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
326457	\N	Julie	Mielzynski	4600	4335	2025-06-24 19:48:54.333136-05	nndz-WkM2eHhyMzVnQT09	4513	t	\N	1	2	33.30		2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
326458	\N	Paige	Newhouse	4600	4335	2025-06-24 19:48:54.333136-05	nndz-WkM2eHg3Lzdodz09	4513	t	\N	1	4	20.00		2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
326459	\N	Ellie	Schwab	4600	4335	2025-06-24 19:48:54.333136-05	nndz-WkM2eHhyMzlnUT09	4513	t	\N	2	6	25.00		2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
326460	\N	Sandi	Fotopoulos	4600	4335	2025-06-24 19:48:54.333136-05	nndz-WkM2eHhyMytoZz09	4513	t	\N	1	0	100.00		2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
326461	\N	Kateri	Rapport	4600	4335	2025-06-24 19:48:54.333136-05	nndz-WkMrK3hMYjZqQT09	4513	t	\N	2	0	100.00		2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
326462	\N	Kate	Salmela	4600	4335	2025-06-24 19:48:54.333136-05	nndz-WkM2eHhyMytqQT09	4513	t	\N	0	0	0.00		2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
326463	\N	Elizabeth	Cargill	4600	4335	2025-06-24 19:48:54.333136-05	nndz-WkMrK3dMajhodz09	4513	t	\N	1	7	12.50		2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
326464	\N	Katie	Kane	4600	4335	2025-06-24 19:48:54.333136-05	nndz-WlNlN3hibi9qUT09	4513	t	\N	4	4	50.00		2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
326465	\N	Jen	McGuaran	4600	4335	2025-06-24 19:48:54.333136-05	nndz-WkMrK3hMbjlnUT09	4513	t	\N	4	2	66.70		2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
326466	\N	Jillian	Nagory	4600	4335	2025-06-24 19:48:54.333136-05	nndz-WlNlN3lMLytqQT09	4513	t	\N	0	5	0.00		2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
326467	\N	Kristen	O'Brien	4600	4335	2025-06-24 19:48:54.333136-05	nndz-WkMrK3hMbjZnQT09	4513	t	\N	0	7	0.00		2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
326468	\N	Tracey	Oberlin	4600	4335	2025-06-24 19:48:54.333136-05	nndz-WlNlN3hyejRqUT09	4513	t	\N	2	6	25.00		2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
326469	\N	Leslie	Young	4600	4335	2025-06-24 19:48:54.333136-05	nndz-WkM2eHhyMy9nZz09	4513	t	\N	1	9	10.00		2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
326470	\N	Caroline	Keating	4608	4335	2025-06-24 19:48:54.333136-05	nndz-WkNDL3didjlqUT09	4513	t	\N	3	2	60.00	C	2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
326471	\N	Anne	Lundberg	4608	4335	2025-06-24 19:48:54.333136-05	nndz-WkMrL3lMejRnUT09	4513	t	\N	2	5	28.60	CC	2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
326472	\N	Kim	Crossgrove	4608	4335	2025-06-24 19:48:54.333136-05	nndz-WkMreHliYjdoZz09	4513	t	\N	2	4	33.30		2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
326473	\N	Lauren	Jerit	4608	4335	2025-06-24 19:48:54.333136-05	nndz-WlNlN3c3LzRndz09	4513	t	\N	4	1	80.00		2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
326474	\N	Kathy	Kennedy	4608	4335	2025-06-24 19:48:54.333136-05	nndz-WkNHNXdyZitndz09	4513	t	\N	4	2	66.70		2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
326475	\N	Clare	Marlin	4608	4335	2025-06-24 19:48:54.333136-05	nndz-WkM2eHg3ajlnUT09	4513	t	\N	3	2	60.00		2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
326476	\N	Meghan	Murphy	4608	4335	2025-06-24 19:48:54.333136-05	nndz-WlNlN3diZjlnUT09	4513	t	\N	4	1	80.00		2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
326477	\N	Betsy	Nielsen	4608	4335	2025-06-24 19:48:54.333136-05	nndz-WkMrL3lMM3hnQT09	4513	t	\N	2	4	33.30		2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
326478	\N	Lauren	Nisbet	4608	4335	2025-06-24 19:48:54.333136-05	nndz-WkMrL3lMM3doUT09	4513	t	\N	3	2	60.00		2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
326479	\N	Pam	Rezek	4608	4335	2025-06-24 19:48:54.333136-05	nndz-WkMrK3dMdi9nZz09	4513	t	\N	2	4	33.30		2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
326480	\N	Mia	Sachs	4608	4335	2025-06-24 19:48:54.333136-05	nndz-WkNHNXlMLzlnQT09	4513	t	\N	1	2	33.30		2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
326481	\N	Katie	Snyder	4608	4335	2025-06-24 19:48:54.333136-05	nndz-WlNlN3dMNzVnQT09	4513	t	\N	3	2	60.00		2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
326482	\N	Amanda	Hollis	4608	4335	2025-06-24 19:48:54.333136-05	nndz-WkMrK3diZi9nZz09	4513	t	\N	8	5	61.50		2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
326483	\N	Laura	Leber	4608	4335	2025-06-24 19:48:54.333136-05	nndz-WkM2eHhycjRqUT09	4513	t	\N	7	0	100.00		2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
326484	\N	Markell	Smith	4608	4335	2025-06-24 19:48:54.333136-05	nndz-WkM2eHhycjdnQT09	4513	t	\N	8	0	100.00		2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
326485	\N	Annie	Heigl	4618	4335	2025-06-24 19:48:54.333136-05	nndz-WkMrK3dMNytnUT09	4513	t	\N	8	2	80.00	C	2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
326486	\N	Kiki	Dickinson	4618	4335	2025-06-24 19:48:54.333136-05	nndz-WkMrL3lMejZoQT09	4513	t	\N	5	1	83.30	CC	2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
326487	\N	Susan	DiFranco	4618	4335	2025-06-24 19:48:54.333136-05	nndz-WlNlN3dycjloZz09	4513	t	\N	4	4	50.00		2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
326488	\N	Lisa	Hill	4618	4335	2025-06-24 19:48:54.333136-05	nndz-WkM2eHhydjRoUT09	4513	t	\N	2	2	50.00		2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
326489	\N	Pamela	Larson	4618	4335	2025-06-24 19:48:54.333136-05	nndz-WkMrK3c3YjZoZz09	4513	t	\N	4	4	50.00		2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
326490	\N	Maria	Mazza	4618	4335	2025-06-24 19:48:54.333136-05	nndz-WkNDL3didjloQT09	4513	t	\N	1	2	33.30		2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
326491	\N	Mary	McGeean	4618	4335	2025-06-24 19:48:54.333136-05	nndz-WkMrK3c3NzZqUT09	4513	t	\N	4	2	66.70		2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
326492	\N	Renee	Schwingbeck	4618	4335	2025-06-24 19:48:54.333136-05	nndz-WkM2eHg3aitqUT09	4513	t	\N	2	1	66.70		2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
326493	\N	Carol	Simner	4618	4335	2025-06-24 19:48:54.333136-05	nndz-WkNDeHdiLzdqUT09	4513	t	\N	0	0	0.00		2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
326494	\N	Alexandria	Tarant	4618	4335	2025-06-24 19:48:54.333136-05	nndz-WkMrK3dyendodz09	4513	t	\N	4	8	33.30		2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
326495	\N	Marissa	DiFranco	4618	4335	2025-06-24 19:48:54.333136-05	nndz-WkMrL3lMLzlnUT09	4513	t	\N	6	11	35.30		2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
326496	\N	Colette	Angarone	4618	4335	2025-06-24 19:48:54.333136-05	nndz-WkM2d3dyYnhqUT09	4513	t	\N	2	2	50.00		2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
326497	\N	Julie	Barry	4618	4335	2025-06-24 19:48:54.333136-05	nndz-WkM2eHhydjVoZz09	4513	t	\N	2	3	40.00		2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
326498	\N	Michelle	Baumann	4618	4335	2025-06-24 19:48:54.333136-05	nndz-WlNlN3hyNzZqUT09	4513	t	\N	5	2	71.40		2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
326499	\N	ciara	bochenek	4618	4335	2025-06-24 19:48:54.333136-05	nndz-WkMrK3diaitqUT09	4513	t	\N	2	6	25.00		2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
326500	\N	Tiffany	Braun	4618	4335	2025-06-24 19:48:54.333136-05	nndz-WkMrK3dibnhoUT09	4513	t	\N	2	2	50.00		2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
326501	\N	Ashley	Curto	4618	4335	2025-06-24 19:48:54.333136-05	nndz-WkMrK3dibjhndz09	4513	t	\N	2	3	40.00		2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
326502	\N	Nicole	Dellaringa	4618	4335	2025-06-24 19:48:54.333136-05	nndz-WkNDL3dicjdqQT09	4513	t	\N	3	2	60.00		2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
326503	\N	Caoilfhionn	Hannon	4618	4335	2025-06-24 19:48:54.333136-05	nndz-WkMrK3dMN3dqUT09	4513	t	\N	3	4	42.90		2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
326504	\N	Nikki	Lazzaro	4618	4335	2025-06-24 19:48:54.333136-05	nndz-WlNlN3c3ZjdnQT09	4513	t	\N	3	3	50.00		2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
326505	\N	Cassi	Noverini	4618	4335	2025-06-24 19:48:54.333136-05	nndz-WkMrK3didjVoUT09	4513	t	\N	4	1	80.00		2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
326506	\N	Agnes	Rygula	4618	4335	2025-06-24 19:48:54.333136-05	nndz-WlNlN3hidi9nZz09	4513	t	\N	1	4	20.00		2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
326507	\N	Meghan	Buckman	4618	4335	2025-06-24 19:48:54.333136-05	nndz-WkMrK3dMbndqQT09	4513	t	\N	6	4	60.00		2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
326508	\N	Christina	Cosgrove	4618	4335	2025-06-24 19:48:54.333136-05	nndz-WlNhOXhiYjZnZz09	4513	t	\N	0	0	0.00		2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
326509	\N	Alice	Hurh	4618	4335	2025-06-24 19:48:54.333136-05	nndz-WkMrL3lMYjRndz09	4513	t	\N	2	2	50.00		2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
326510	\N	Sasha	Long	4618	4335	2025-06-24 19:48:54.333136-05	nndz-WkMrN3hyNytndz09	4513	t	\N	2	2	50.00		2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
326511	\N	Jamie	Russo	4618	4335	2025-06-24 19:48:54.333136-05	nndz-WkM2eHhydjVoQT09	4513	t	\N	7	1	87.50		2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
326512	\N	Jennifer	Price	4640	4335	2025-06-24 19:48:54.333136-05	nndz-WkM2eHhyZjZodz09	4513	t	\N	3	6	33.30	C	2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
326513	\N	Colleen	Simpson	4640	4335	2025-06-24 19:48:54.333136-05	nndz-WkNDL3diM3hnZz09	4513	t	\N	1	7	12.50	CC	2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
326514	\N	Tara	Baker	4640	4335	2025-06-24 19:48:54.333136-05	nndz-WkMrK3diZjdqUT09	4513	t	\N	2	3	40.00		2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
326515	\N	Jenelle	Chalmers	4640	4335	2025-06-24 19:48:54.333136-05	nndz-WkM2eHhyZjdqUT09	4513	t	\N	3	4	42.90		2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
326516	\N	Patricia	Danielak	4640	4335	2025-06-24 19:48:54.333136-05	nndz-WlNlN3hiMzlqQT09	4513	t	\N	3	2	60.00		2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
326517	\N	Katie	Gano	4640	4335	2025-06-24 19:48:54.333136-05	nndz-WkM2eHliLzdnQT09	4513	t	\N	0	1	0.00		2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
326518	\N	Sharon	Hofmann	4640	4335	2025-06-24 19:48:54.333136-05	nndz-WlNlN3c3ZitnUT09	4513	t	\N	3	2	60.00		2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
326519	\N	Annie	Laughton	4640	4335	2025-06-24 19:48:54.333136-05	nndz-WlNlN3hiLytqQT09	4513	t	\N	2	2	50.00		2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
326520	\N	Brittany	Moore	4640	4335	2025-06-24 19:48:54.333136-05	nndz-WkM2eHhyZjZoQT09	4513	t	\N	2	5	28.60		2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
326521	\N	Katherine	Moran	4640	4335	2025-06-24 19:48:54.333136-05	nndz-WkMrK3lMYjhnUT09	4513	t	\N	0	0	0.00		2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
326522	\N	Jenn	Phillips	4640	4335	2025-06-24 19:48:54.333136-05	nndz-WkNHNXc3cnhqUT09	4513	t	\N	1	0	100.00		2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
326523	\N	Lauren	Pickrell	4640	4335	2025-06-24 19:48:54.333136-05	nndz-WkM2eHhyZnhndz09	4513	t	\N	0	1	0.00		2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
326524	\N	Mliz	Simonds	4640	4335	2025-06-24 19:48:54.333136-05	nndz-WkM2eHhyZjZnQT09	4513	t	\N	0	0	0.00		2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
326525	\N	Annie	Watson	4640	4335	2025-06-24 19:48:54.333136-05	nndz-WkM2eHhyZjZqUT09	4513	t	\N	1	6	14.30		2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
326526	\N	Janet	Scholl	4640	4335	2025-06-24 19:48:54.333136-05	nndz-WkM2eHhyZjZnUT09	4513	t	\N	0	0	0.00		2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
326527	\N	Amy	Chung	4640	4335	2025-06-24 19:48:54.333136-05	nndz-WkM2eHhyZjdoZz09	4513	t	\N	0	1	0.00		2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
326528	\N	Mary	Jo Lestingi	4640	4335	2025-06-24 19:48:54.333136-05	nndz-WkM2eHg3ejZodz09	4513	t	\N	2	1	66.70		2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
326529	\N	REBECCA	WADMAN	4640	4335	2025-06-24 19:48:54.333136-05	nndz-WlNlN3hiNzRoZz09	4513	t	\N	11	1	91.70		2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
326530	\N	Claire	Winnard	4640	4335	2025-06-24 19:48:54.333136-05	nndz-WlNlNnhiei9nUT09	4513	t	\N	7	2	77.80		2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
326531	\N	Jennifer	Christensen	4640	4335	2025-06-24 19:48:54.333136-05	nndz-WkM2eHhyZitnZz09	4513	t	\N	0	3	0.00		2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
326532	\N	Betsy	Nelson	4640	4335	2025-06-24 19:48:54.333136-05	nndz-WkM2eHhyZnhnQT09	4513	t	\N	4	4	50.00		2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
326533	\N	Amanda	Schallman	4571	4338	2025-06-24 19:48:54.333136-05	nndz-WkMrK3c3bjdoZz09	4513	t	\N	4	4	50.00	C	2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
326534	\N	Elaine	Stern	4571	4338	2025-06-24 19:48:54.333136-05	nndz-WkM2eHhyNzZodz09	4513	t	\N	1	6	14.30	CC	2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
326535	\N	Margaret	Adess	4571	4338	2025-06-24 19:48:54.333136-05	nndz-WlNlNndyYjhnZz09	4513	t	\N	1	2	33.30		2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
326536	\N	Romy	Block-Posner	4571	4338	2025-06-24 19:48:54.333136-05	nndz-WkMrK3liMzloQT09	4513	t	\N	0	1	0.00		2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
326537	\N	Alison	Bronson	4571	4338	2025-06-24 19:48:54.333136-05	nndz-WkMrK3dyejlqUT09	4513	t	\N	3	4	42.90		2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
326538	\N	Dana	Harf	4571	4338	2025-06-24 19:48:54.333136-05	nndz-WkMrK3c3bjdnQT09	4513	t	\N	0	2	0.00		2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
326539	\N	Amy	Israel	4571	4338	2025-06-24 19:48:54.333136-05	nndz-WkM2eHhyNzdodz09	4513	t	\N	5	1	83.30		2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
326540	\N	Brooke	Kauf	4571	4338	2025-06-24 19:48:54.333136-05	nndz-WkNDL3diajRnZz09	4513	t	\N	0	4	0.00		2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
326541	\N	Mimi	Marks	4571	4338	2025-06-24 19:48:54.333136-05	nndz-WkM2eHhyNzdnUT09	4513	t	\N	1	3	25.00		2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
326542	\N	Danielle	Pearl	4571	4338	2025-06-24 19:48:54.333136-05	nndz-WkNHNXc3YjhqQT09	4513	t	\N	1	4	20.00		2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
326543	\N	Stacey	Price	4571	4338	2025-06-24 19:48:54.333136-05	nndz-WkM2eHhyNzRnQT09	4513	t	\N	3	2	60.00		2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
326544	\N	Andrea	Rubin	4571	4338	2025-06-24 19:48:54.333136-05	nndz-WkM2eHhyNzdqQT09	4513	t	\N	0	2	0.00		2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
326545	\N	Jenny	Stern	4571	4338	2025-06-24 19:48:54.333136-05	nndz-WkM2eHhyNzZoZz09	4513	t	\N	2	2	50.00		2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
326546	\N	Diana	Vdovets	4571	4338	2025-06-24 19:48:54.333136-05	nndz-WlNlN3c3ejlndz09	4513	t	\N	0	1	0.00		2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
326547	\N	Marissa	Fetter Hochster	4571	4338	2025-06-24 19:48:54.333136-05	nndz-WkMrK3liajlnQT09	4513	t	\N	5	5	50.00		2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
326548	\N	Ellen	Gussin	4571	4338	2025-06-24 19:48:54.333136-05	nndz-WkNDL3diMzloQT09	4513	t	\N	0	0	0.00		2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
326549	\N	Barbara	Lincoln	4571	4338	2025-06-24 19:48:54.333136-05	nndz-WkM2eHhyNzdoZz09	4513	t	\N	0	1	0.00		2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
326550	\N	Jen	Rosen	4571	4338	2025-06-24 19:48:54.333136-05	nndz-WkM2eHhyNzdqUT09	4513	t	\N	0	0	0.00		2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
326551	\N	Lynne	Levey	4574	4338	2025-06-24 19:48:54.333136-05	nndz-WlNlN3g3cnhodz09	4513	t	\N	4	3	57.10	C	2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
326552	\N	Lesley	Sarnoff	4574	4338	2025-06-24 19:48:54.333136-05	nndz-WkMrK3hidnhnZz09	4513	t	\N	5	3	62.50	CC	2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
326553	\N	Sara	Cherney	4574	4338	2025-06-24 19:48:54.333136-05	nndz-WlNlN3dMejVnQT09	4513	t	\N	3	3	50.00		2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
326554	\N	Bernadette	Foley	4574	4338	2025-06-24 19:48:54.333136-05	nndz-WlNlOXdMaitqUT09	4513	t	\N	1	3	25.00		2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
326555	\N	julie	lakonishok	4574	4338	2025-06-24 19:48:54.333136-05	nndz-WkMreHhyYi9ndz09	4513	t	\N	3	3	50.00		2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
326556	\N	Danielle	Sandler	4574	4338	2025-06-24 19:48:54.333136-05	nndz-WkMrK3liZnhodz09	4513	t	\N	0	0	0.00		2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
326557	\N	Claudia	Schumer	4574	4338	2025-06-24 19:48:54.333136-05	nndz-WlNlN3diei9oUT09	4513	t	\N	1	4	20.00		2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
326558	\N	Dora	Snyder	4574	4338	2025-06-24 19:48:54.333136-05	nndz-WkMrK3dMN3doUT09	4513	t	\N	5	2	71.40		2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
326559	\N	Julie	Zwick	4574	4338	2025-06-24 19:48:54.333136-05	nndz-WkMrK3dybnhqQT09	4513	t	\N	4	2	66.70		2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
326560	\N	Rebecca	Graines	4574	4338	2025-06-24 19:48:54.333136-05	nndz-WkMrK3dybitnQT09	4513	t	\N	4	3	57.10		2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
326561	\N	Debra	kissen	4574	4338	2025-06-24 19:48:54.333136-05	nndz-WlNlN3diNy9oQT09	4513	t	\N	6	1	85.70		2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
326562	\N	Marcy	Zoller	4574	4338	2025-06-24 19:48:54.333136-05	nndz-WkMrK3g3cjZodz09	4513	t	\N	4	4	50.00		2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
326563	\N	Wendy	Bremen	4574	4338	2025-06-24 19:48:54.333136-05	nndz-WkNDOHlMbjlnQT09	4513	t	\N	5	2	71.40		2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
326564	\N	Mirabell	Lad	4574	4338	2025-06-24 19:48:54.333136-05	nndz-WlNlOXdMandoZz09	4513	t	\N	0	0	0.00		2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
326565	\N	Laura	Senner	4579	4338	2025-06-24 19:48:54.333136-05	nndz-WkNDL3didjVnQT09	4513	t	\N	0	5	0.00	C	2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
326566	\N	Gina	Pistorio	4579	4338	2025-06-24 19:48:54.333136-05	nndz-WkNDL3didjVnUT09	4513	t	\N	1	6	14.30	CC	2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
326567	\N	Marilyn	Arthurs	4579	4338	2025-06-24 19:48:54.333136-05	nndz-WkNHNXc3M3hnQT09	4513	t	\N	0	0	0.00		2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
326568	\N	Emily	Buhle	4579	4338	2025-06-24 19:48:54.333136-05	nndz-WkMrL3lMcitoZz09	4513	t	\N	2	4	33.30		2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
326569	\N	Irene	Curry	4579	4338	2025-06-24 19:48:54.333136-05	nndz-WkMrK3dyLy9nZz09	4513	t	\N	3	2	60.00		2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
326570	\N	Amy	DeMarino	4579	4338	2025-06-24 19:48:54.333136-05	nndz-WkMrK3hiMy9nUT09	4513	t	\N	3	5	37.50		2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
326571	\N	Sarah	Donlan	4579	4338	2025-06-24 19:48:54.333136-05	nndz-WkMrK3dyLy9odz09	4513	t	\N	0	0	0.00		2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
326572	\N	Teresa	Ferguson	4579	4338	2025-06-24 19:48:54.333136-05	nndz-WlNlN3diNzlndz09	4513	t	\N	0	0	0.00		2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
326573	\N	Kim	Flanagan	4579	4338	2025-06-24 19:48:54.333136-05	nndz-WkM2eHhyNzhqQT09	4513	t	\N	2	3	40.00		2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
326574	\N	Annie	Gray	4579	4338	2025-06-24 19:48:54.333136-05	nndz-WlNlN3diNzlnZz09	4513	t	\N	4	4	50.00		2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
326575	\N	Leticia	Guerra-Shinozaki	4579	4338	2025-06-24 19:48:54.333136-05	nndz-WkNDL3didjVndz09	4513	t	\N	3	4	42.90		2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
326576	\N	Kris	Matthews Blase	4579	4338	2025-06-24 19:48:54.333136-05	nndz-WkM2eHhyNzhoZz09	4513	t	\N	0	5	0.00		2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
326577	\N	Megan	Nick	4579	4338	2025-06-24 19:48:54.333136-05	nndz-WkM2eHhyN3hqQT09	4513	t	\N	2	5	28.60		2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
326578	\N	Celia	Sinclair	4579	4338	2025-06-24 19:48:54.333136-05	nndz-WkM2eHhyNy9ndz09	4513	t	\N	2	4	33.30		2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
326579	\N	Julie	Balber	4579	4338	2025-06-24 19:48:54.333136-05	nndz-WkNHNXc3M3hqUT09	4513	t	\N	0	0	0.00		2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
326580	\N	Carol	Dammrich	4579	4338	2025-06-24 19:48:54.333136-05	nndz-WkNDOHlMZjZnZz09	4513	t	\N	0	0	0.00		2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
326581	\N	Susan	Gallun	4579	4338	2025-06-24 19:48:54.333136-05	nndz-WkNDL3didjdoUT09	4513	t	\N	0	0	0.00		2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
326582	\N	Terese	Lomasney	4579	4338	2025-06-24 19:48:54.333136-05	nndz-WkM2eHhyNy9oZz09	4513	t	\N	0	0	0.00		2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
326583	\N	Stacy	Reynolds	4579	4338	2025-06-24 19:48:54.333136-05	nndz-WkM2eHhyLzRnQT09	4513	t	\N	1	2	33.30		2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
326584	\N	Taylor	Rosellini	4579	4338	2025-06-24 19:48:54.333136-05	nndz-WkM2eHhyLzVoZz09	4513	t	\N	5	3	62.50		2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
326585	\N	Annie	Rothe	4579	4338	2025-06-24 19:48:54.333136-05	nndz-WkM2eHhyLzVnUT09	4513	t	\N	7	4	63.60		2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
326586	\N	Margaret	LeFevour	4579	4338	2025-06-24 19:48:54.333136-05	nndz-WkMrK3diZitoUT09	4513	t	\N	2	4	33.30		2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
326587	\N	Mary	Mcmanus	4579	4338	2025-06-24 19:48:54.333136-05	nndz-WkMrK3hicjdndz09	4513	t	\N	2	5	28.60		2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
326588	\N	Anne	Sullivan	4579	4338	2025-06-24 19:48:54.333136-05	nndz-WlNlN3diNzlqQT09	4513	t	\N	3	0	100.00		2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
326589	\N	Mila	Sobinsky	4595	4338	2025-06-24 19:48:54.333136-05	nndz-WkM2eHhyejhqQT09	4513	t	\N	1	8	11.10	C	2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
326590	\N	Ingrid	Michael	4595	4338	2025-06-24 19:48:54.333136-05	nndz-WkM2eHhyejhnUT09	4513	t	\N	1	3	25.00	CC	2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
326591	\N	Aneri	Bhansali	4595	4338	2025-06-24 19:48:54.333136-05	nndz-WlNlNnlici9oQT09	4513	t	\N	0	0	0.00		2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
326592	\N	Anokhi	Bock	4595	4338	2025-06-24 19:48:54.333136-05	nndz-WlNlNnliL3dodz09	4513	t	\N	0	2	0.00		2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
326593	\N	Kim	Bradley	4595	4338	2025-06-24 19:48:54.333136-05	nndz-WkMrK3dyejZnZz09	4513	t	\N	0	5	0.00		2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
326594	\N	Cheryl	Camardo	4595	4338	2025-06-24 19:48:54.333136-05	nndz-WkMrK3dyNzRndz09	4513	t	\N	0	3	0.00		2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
326595	\N	Fran	Chana	4595	4338	2025-06-24 19:48:54.333136-05	nndz-WlNlNnhyejRnZz09	4513	t	\N	1	1	50.00		2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
326596	\N	Lisa	Chang	4595	4338	2025-06-24 19:48:54.333136-05	nndz-WkM2eHhyejlqQT09	4513	t	\N	0	7	0.00		2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
326597	\N	Betty	Collins	4595	4338	2025-06-24 19:48:54.333136-05	nndz-WkMrK3hicjVnQT09	4513	t	\N	2	4	33.30		2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
326598	\N	Deardra	Cook	4595	4338	2025-06-24 19:48:54.333136-05	nndz-WkM2eHhyejhoUT09	4513	t	\N	3	3	50.00		2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
326599	\N	Therese	Dempsey	4595	4338	2025-06-24 19:48:54.333136-05	nndz-WlNlNnhybjRqQT09	4513	t	\N	0	0	0.00		2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
326600	\N	Kimberly	Egan	4595	4338	2025-06-24 19:48:54.333136-05	nndz-WlNlNnlMNzdodz09	4513	t	\N	0	0	0.00		2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
326601	\N	Jennifer	Hoogasian	4595	4338	2025-06-24 19:48:54.333136-05	nndz-WkMrK3hMNzdnQT09	4513	t	\N	1	1	50.00		2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
326602	\N	Lia	Landis	4595	4338	2025-06-24 19:48:54.333136-05	nndz-WlNlNnhiMzlnUT09	4513	t	\N	0	0	0.00		2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
326603	\N	Meg	Lynch	4595	4338	2025-06-24 19:48:54.333136-05	nndz-WkNDL3dMM3doUT09	4513	t	\N	0	0	0.00		2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
326604	\N	Astrid	Piccolo	4595	4338	2025-06-24 19:48:54.333136-05	nndz-WkNDL3didjRndz09	4513	t	\N	1	3	25.00		2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
326605	\N	Carrie	Ravagnie	4595	4338	2025-06-24 19:48:54.333136-05	nndz-WkMrK3lMcjhnZz09	4513	t	\N	1	2	33.30		2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
326606	\N	Kristin	Rupp	4595	4338	2025-06-24 19:48:54.333136-05	nndz-WlNlNnhidnhoUT09	4513	t	\N	1	1	50.00		2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
326607	\N	Lisa	Schilling	4595	4338	2025-06-24 19:48:54.333136-05	nndz-WkM2eHlMci9oUT09	4513	t	\N	2	1	66.70		2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
326608	\N	Julia	Flannery	4595	4338	2025-06-24 19:48:54.333136-05	nndz-WlNhNnlMMzZodz09	4513	t	\N	5	6	45.50		2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
326609	\N	Vanessa	Fox	4595	4338	2025-06-24 19:48:54.333136-05	nndz-WlNlNnhibjhnQT09	4513	t	\N	3	3	50.00		2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
326610	\N	Emily	Schwartz	4601	4338	2025-06-24 19:48:54.333136-05	nndz-WkM2eHhyM3hnZz09	4513	t	\N	3	8	27.30	C	2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
326611	\N	Stacey	Greenberg	4601	4338	2025-06-24 19:48:54.333136-05	nndz-WkM2eHhyM3hnUT09	4513	t	\N	0	4	0.00	CC	2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
326612	\N	Alexis	Bednyak	4601	4338	2025-06-24 19:48:54.333136-05	nndz-WkMreHliM3doQT09	4513	t	\N	2	1	66.70		2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
326613	\N	Lindsey	Bernick	4601	4338	2025-06-24 19:48:54.333136-05	nndz-WlNlOXhycndodz09	4513	t	\N	0	0	0.00		2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
326614	\N	anna	domb	4601	4338	2025-06-24 19:48:54.333136-05	nndz-WlNlOXdiNytqQT09	4513	t	\N	0	5	0.00		2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
326615	\N	Chris	Fixler	4601	4338	2025-06-24 19:48:54.333136-05	nndz-WkMreHg3NzhnUT09	4513	t	\N	3	7	30.00		2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
326616	\N	Molly	Friedlich	4601	4338	2025-06-24 19:48:54.333136-05	nndz-WkMreHlibjhodz09	4513	t	\N	4	4	50.00		2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
326617	\N	Rebecca	Gillett	4601	4338	2025-06-24 19:48:54.333136-05	nndz-WlNlNng3bitndz09	4513	t	\N	1	3	25.00		2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
326618	\N	Sara	Greenberg	4601	4338	2025-06-24 19:48:54.333136-05	nndz-WlNlNndyZnhndz09	4513	t	\N	0	0	0.00		2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
326619	\N	Shana	Greenberg	4601	4338	2025-06-24 19:48:54.333136-05	nndz-WlNlN3liYitoQT09	4513	t	\N	0	0	0.00		2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
326620	\N	Jenna	Saltzman	4601	4338	2025-06-24 19:48:54.333136-05	nndz-WlNlN3liN3hnZz09	4513	t	\N	0	0	0.00		2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
326621	\N	Orian	Schwartz	4601	4338	2025-06-24 19:48:54.333136-05	nndz-WlNlOXliYjVodz09	4513	t	\N	1	3	25.00		2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
326622	\N	Samantha	Siegel	4601	4338	2025-06-24 19:48:54.333136-05	nndz-WlNlOXdMYndnZz09	4513	t	\N	2	3	40.00		2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
326623	\N	Stacy	Zendel	4601	4338	2025-06-24 19:48:54.333136-05	nndz-WkM2eHhyM3hqUT09	4513	t	\N	0	5	0.00		2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
326624	\N	Robin	Miller	4601	4338	2025-06-24 19:48:54.333136-05	nndz-WlNlOXhMai9oQT09	4513	t	\N	1	7	12.50		2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
326625	\N	Erin	Pritzker	4601	4338	2025-06-24 19:48:54.333136-05	nndz-WlNlN3hyZi9ndz09	4513	t	\N	3	7	30.00		2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
326626	\N	Jill	Smiley	4601	4338	2025-06-24 19:48:54.333136-05	nndz-WkMreHlicnhnZz09	4513	t	\N	0	0	0.00		2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
326627	\N	Alyssa	Swilky	4601	4338	2025-06-24 19:48:54.333136-05	nndz-WlNhNnc3ei9nUT09	4513	t	\N	1	1	50.00		2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
326628	\N	Anna	O’donnell	4611	4338	2025-06-24 19:48:54.333136-05	nndz-WkM2eHhycjhodz09	4513	t	\N	2	4	33.30	C	2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
326629	\N	Brooke	Aslesen	4611	4338	2025-06-24 19:48:54.333136-05	nndz-WkM2eHhycjhnUT09	4513	t	\N	1	3	25.00		2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
326630	\N	Susan	Burden	4611	4338	2025-06-24 19:48:54.333136-05	nndz-WkM2d3c3djVoUT09	4513	t	\N	2	4	33.30		2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
326631	\N	Mary	Helen Cronin	4611	4338	2025-06-24 19:48:54.333136-05	nndz-WkM2eHhycjhoUT09	4513	t	\N	2	2	50.00		2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
326632	\N	molly	haravon	4611	4338	2025-06-24 19:48:54.333136-05	nndz-WkMrL3lMMzdnZz09	4513	t	\N	4	1	80.00		2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
326633	\N	Halle	Koch	4611	4338	2025-06-24 19:48:54.333136-05	nndz-WkM2eHhycjhnZz09	4513	t	\N	2	4	33.30		2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
326634	\N	Kristin	McColgan	4611	4338	2025-06-24 19:48:54.333136-05	nndz-WkNHNXdMMzZndz09	4513	t	\N	5	4	55.60		2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
326635	\N	Jennifer	Sorrow	4611	4338	2025-06-24 19:48:54.333136-05	nndz-WkNHNXdMMzVqUT09	4513	t	\N	4	4	50.00		2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
326636	\N	Clare	Martin	4611	4338	2025-06-24 19:48:54.333136-05	nndz-WkM2eHhycjhqUT09	4513	t	\N	2	5	28.60		2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
326637	\N	Stephanie	Morrisroe	4611	4338	2025-06-24 19:48:54.333136-05	nndz-WkM2eHhyci9oUT09	4513	t	\N	2	4	33.30		2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
326638	\N	Jordan	Daul	4611	4338	2025-06-24 19:48:54.333136-05	nndz-WkM2eHhycjhnQT09	4513	t	\N	1	4	20.00		2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
326639	\N	AMY	MCCANN	4611	4338	2025-06-24 19:48:54.333136-05	nndz-WkMrK3dybndnUT09	4513	t	\N	6	5	54.50		2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
326640	\N	Tracey	Weber	4611	4338	2025-06-24 19:48:54.333136-05	nndz-WlNlL3hyYnhnUT09	4513	t	\N	1	1	50.00		2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
326641	\N	Taylor	Kehoe	4611	4338	2025-06-24 19:48:54.333136-05	nndz-WkMrL3lMLzlodz09	4513	t	\N	3	4	42.90		2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
326642	\N	Karen	Walker	4635	4338	2025-06-24 19:48:54.333136-05	nndz-WkM2d3dMYjhqUT09	4513	t	\N	6	5	54.50	C	2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
326643	\N	Jennifer	Zandpour	4635	4338	2025-06-24 19:48:54.333136-05	nndz-WkM2eHhyajdqUT09	4513	t	\N	7	2	77.80	CC	2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
326644	\N	Kelly	Beck	4635	4338	2025-06-24 19:48:54.333136-05	nndz-WlNlN3dyajlndz09	4513	t	\N	10	2	83.30		2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
326645	\N	Susan	Hering	4635	4338	2025-06-24 19:48:54.333136-05	nndz-WkNDL3diMy9oQT09	4513	t	\N	2	6	25.00		2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
326646	\N	Jenny	McNitt	4635	4338	2025-06-24 19:48:54.333136-05	nndz-WkMrL3lMZjloQT09	4513	t	\N	0	0	0.00		2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
326647	\N	Kate	Neal	4635	4338	2025-06-24 19:48:54.333136-05	nndz-WkNDL3dicjZoQT09	4513	t	\N	1	0	100.00		2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
326648	\N	Carolyn	Passen	4635	4338	2025-06-24 19:48:54.333136-05	nndz-WkM2eHhyajdndz09	4513	t	\N	3	2	60.00		2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
326649	\N	Janet	Ryan	4635	4338	2025-06-24 19:48:54.333136-05	nndz-WlNlNnlMZi9nQT09	4513	t	\N	0	1	0.00		2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
326650	\N	Amanda	Sundt	4635	4338	2025-06-24 19:48:54.333136-05	nndz-WkNHNXdMdjVndz09	4513	t	\N	2	3	40.00		2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
326651	\N	Ashley	Sutphen	4635	4338	2025-06-24 19:48:54.333136-05	nndz-WkM2eHhyajlqQT09	4513	t	\N	5	1	83.30		2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
326652	\N	Lauren	Yarbrough	4635	4338	2025-06-24 19:48:54.333136-05	nndz-WlNlN3dyajlnZz09	4513	t	\N	2	1	66.70		2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
326653	\N	Jill	Beckstedt	4635	4338	2025-06-24 19:48:54.333136-05	nndz-WkNDL3diajRodz09	4513	t	\N	1	2	33.30		2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
326654	\N	Caitlin	Eck	4635	4338	2025-06-24 19:48:54.333136-05	nndz-WkMrL3lMbi9nUT09	4513	t	\N	1	6	14.30		2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
326655	\N	Jennifer	Mackey	4635	4338	2025-06-24 19:48:54.333136-05	nndz-WkM2eHhyajdodz09	4513	t	\N	4	3	57.10		2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
326656	\N	Heather	Hoeppner	4635	4338	2025-06-24 19:48:54.333136-05	nndz-WkMrK3c3Zi9oUT09	4513	t	\N	4	2	66.70		2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
326657	\N	Daley	Spiegel	4635	4338	2025-06-24 19:48:54.333136-05	nndz-WlNlN3g3ci9nUT09	4513	t	\N	5	4	55.60		2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
326658	\N	Beth	Wechsler	4642	4338	2025-06-24 19:48:54.333136-05	nndz-WkMreHdiZjhnUT09	4513	t	\N	7	2	77.80	C	2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
326659	\N	Alexis	Kuncel	4642	4338	2025-06-24 19:48:54.333136-05	nndz-WkMreHdMLzRnQT09	4513	t	\N	5	1	83.30	CC	2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
326660	\N	Megan	Ausenbaugh	4642	4338	2025-06-24 19:48:54.333136-05	nndz-WkMrK3lMbjVoZz09	4513	t	\N	5	3	62.50		2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
326661	\N	Melissa	Brodahl	4642	4338	2025-06-24 19:48:54.333136-05	nndz-WkMrK3hMajlnZz09	4513	t	\N	1	1	50.00		2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
326662	\N	Sara	Forrest	4642	4338	2025-06-24 19:48:54.333136-05	nndz-WkMrN3hiM3dnQT09	4513	t	\N	6	2	75.00		2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
326663	\N	Lisa	Goldman	4642	4338	2025-06-24 19:48:54.333136-05	nndz-WkMrN3hiM3dndz09	4513	t	\N	7	2	77.80		2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
326664	\N	Erin	Heywood	4642	4338	2025-06-24 19:48:54.333136-05	nndz-WkMreHdMNzZoZz09	4513	t	\N	6	2	75.00		2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
326665	\N	Ann	Norton	4642	4338	2025-06-24 19:48:54.333136-05	nndz-WlNlN3c3N3dodz09	4513	t	\N	3	0	100.00		2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
326666	\N	Laura	Sardegna	4642	4338	2025-06-24 19:48:54.333136-05	nndz-WkM2eHliNzRnUT09	4513	t	\N	4	1	80.00		2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
326667	\N	Constance	Schuller	4642	4338	2025-06-24 19:48:54.333136-05	nndz-WlNlOXhMci9odz09	4513	t	\N	5	1	83.30		2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
326668	\N	Kathryn	Birch	4642	4338	2025-06-24 19:48:54.333136-05	nndz-WlNlNHlMZjRqQT09	4513	t	\N	6	5	54.50		2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
326669	\N	Maggie	Burke	4642	4338	2025-06-24 19:48:54.333136-05	nndz-WkMreHdMLzVqQT09	4513	t	\N	13	1	92.90		2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
326670	\N	Mandy	Hartman	4642	4338	2025-06-24 19:48:54.333136-05	nndz-WkMrK3hyanhoZz09	4513	t	\N	3	3	50.00		2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
326671	\N	Annie	Smith	4642	4338	2025-06-24 19:48:54.333136-05	nndz-WkMrK3hidjZnZz09	4513	t	\N	12	1	92.30		2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
326672	\N	Sarah	Hall	4646	4338	2025-06-24 19:48:54.333136-05	nndz-WkM2eHg3ejZoZz09	4513	t	\N	6	1	85.70	C	2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
326673	\N	Stacy	Weiss - WINN	4646	4338	2025-06-24 19:48:54.333136-05	nndz-WkMreHdMejdqUT09	4513	t	\N	7	0	100.00	CC	2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
326674	\N	Alexis	Armstrong	4646	4338	2025-06-24 19:48:54.333136-05	nndz-WkMreHhyZjhqQT09	4513	t	\N	5	1	83.30		2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
326675	\N	Liz	Budig	4646	4338	2025-06-24 19:48:54.333136-05	nndz-WlNlN3dybjRoQT09	4513	t	\N	8	1	88.90		2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
326676	\N	Tobi	Kalish	4646	4338	2025-06-24 19:48:54.333136-05	nndz-WkMrK3dMbnhnZz09	4513	t	\N	3	3	50.00		2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
326677	\N	Rebecca	Knohl	4646	4338	2025-06-24 19:48:54.333136-05	nndz-WkMrK3diMy9qUT09	4513	t	\N	3	3	50.00		2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
326678	\N	Kirsten	Lestina	4646	4338	2025-06-24 19:48:54.333136-05	nndz-WkMrK3diajdndz09	4513	t	\N	0	0	0.00		2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
326679	\N	Libby	Splithoff	4646	4338	2025-06-24 19:48:54.333136-05	nndz-WlNlN3liM3dqQT09	4513	t	\N	5	0	100.00		2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
326680	\N	Amy	Steinback	4646	4338	2025-06-24 19:48:54.333136-05	nndz-WlNlNnhyNzZnUT09	4513	t	\N	3	2	60.00		2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
326681	\N	Jenna	Summerford	4646	4338	2025-06-24 19:48:54.333136-05	nndz-WkMrK3hycjZnUT09	4513	t	\N	4	2	66.70		2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
326682	\N	Cristina	Aliagas	4646	4338	2025-06-24 19:48:54.333136-05	nndz-WkM2d3hidnhoZz09	4513	t	\N	8	2	80.00		2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
326683	\N	Anna	Beimford	4646	4338	2025-06-24 19:48:54.333136-05	nndz-WlNlOXhydndqUT09	4513	t	\N	1	0	100.00		2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
326684	\N	Susana	Castella	4646	4338	2025-06-24 19:48:54.333136-05	nndz-WkM2d3hidnhoUT09	4513	t	\N	4	1	80.00		2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
326685	\N	Meredith	Goodspeed	4646	4338	2025-06-24 19:48:54.333136-05	nndz-WlNlN3diZjlodz09	4513	t	\N	7	2	77.80		2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
326686	\N	Emma	Khoury	4646	4338	2025-06-24 19:48:54.333136-05	nndz-WlNlN3hiMzVqQT09	4513	t	\N	6	4	60.00		2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
326687	\N	Elizabeth	Muzik	4646	4338	2025-06-24 19:48:54.333136-05	nndz-WkMrL3lMYndoQT09	4513	t	\N	7	0	100.00		2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
326688	\N	Meg	Zuehl	4646	4338	2025-06-24 19:48:54.333136-05	nndz-WkM2d3hidnhqQT09	4513	t	\N	10	6	62.50		2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
326689	\N	Bridget	Leffingwell	4649	4338	2025-06-24 19:48:54.333136-05	nndz-WkMrK3hMcitnZz09	4513	t	\N	5	3	62.50	C	2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
326690	\N	Kathrin	Martens-Salgat	4649	4338	2025-06-24 19:48:54.333136-05	nndz-WkMrK3hMMy9nUT09	4513	t	\N	7	6	53.80	CC	2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
326691	\N	Lindsey	Bornholdt	4649	4338	2025-06-24 19:48:54.333136-05	nndz-WlNlNng3ZitoZz09	4513	t	\N	4	2	66.70		2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
326692	\N	Mallory	Boyens	4649	4338	2025-06-24 19:48:54.333136-05	nndz-WkMrK3hMajdnZz09	4513	t	\N	3	1	75.00		2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
326693	\N	Keunae	Choe	4649	4338	2025-06-24 19:48:54.333136-05	nndz-WkM2eHliejhoQT09	4513	t	\N	0	0	0.00		2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
326694	\N	Megan	Hadler	4649	4338	2025-06-24 19:48:54.333136-05	nndz-WkMrK3g3L3hnQT09	4513	t	\N	5	1	83.30		2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
326695	\N	Stephanie	Knauff	4649	4338	2025-06-24 19:48:54.333136-05	nndz-WkMrK3hMbi9nQT09	4513	t	\N	6	2	75.00		2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
326696	\N	Anna	O'Connor	4649	4338	2025-06-24 19:48:54.333136-05	nndz-WkM2eHhyMy9nUT09	4513	t	\N	2	1	66.70		2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
326697	\N	Stephanie	Rickmeier	4649	4338	2025-06-24 19:48:54.333136-05	nndz-WkMrK3hMajhqQT09	4513	t	\N	0	0	0.00		2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
326698	\N	Kamila	Urso	4649	4338	2025-06-24 19:48:54.333136-05	nndz-WkMreHc3Nzlndz09	4513	t	\N	6	3	66.70		2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
326699	\N	Kimberly	Denapoli	4649	4338	2025-06-24 19:48:54.333136-05	nndz-WkMrK3g3ejlnUT09	4513	t	\N	11	4	73.30		2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
326700	\N	Rae	Dobosh	4649	4338	2025-06-24 19:48:54.333136-05	nndz-WkMrK3hMbjVqQT09	4513	t	\N	3	3	50.00		2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
326701	\N	Kara	Szot	4649	4338	2025-06-24 19:48:54.333136-05	nndz-WlNhNnliL3dnZz09	4513	t	\N	6	7	46.20		2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
326702	\N	Laura	Copilevitz	4572	4339	2025-06-24 19:48:54.333136-05	nndz-WkM2eHlicjdqQT09	4513	t	\N	7	4	63.60	C	2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
326703	\N	Lauren	Rosen	4572	4339	2025-06-24 19:48:54.333136-05	nndz-WkMrK3lMLy9ndz09	4513	t	\N	1	5	16.70	CC	2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
326704	\N	Jordyn	Berger	4572	4339	2025-06-24 19:48:54.333136-05	nndz-WlNlN3hicnhoQT09	4513	t	\N	1	3	25.00		2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
326705	\N	Jacki	Block	4572	4339	2025-06-24 19:48:54.333136-05	nndz-WlNlN3hicitndz09	4513	t	\N	0	0	0.00		2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
326706	\N	Dawn	Breiter	4572	4339	2025-06-24 19:48:54.333136-05	nndz-WkNDL3diL3hodz09	4513	t	\N	1	2	33.30		2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
326707	\N	Courtney	Farrell	4572	4339	2025-06-24 19:48:54.333136-05	nndz-WkMrK3lMLytoUT09	4513	t	\N	5	4	55.60		2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
326708	\N	Holly	Goldberg	4572	4339	2025-06-24 19:48:54.333136-05	nndz-WkM2d3g3bjVnUT09	4513	t	\N	4	2	66.70		2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
326709	\N	Mary	McAnally	4572	4339	2025-06-24 19:48:54.333136-05	nndz-WlNlN3liLzdodz09	4513	t	\N	3	2	60.00		2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
326710	\N	Holly	Metzger	4572	4339	2025-06-24 19:48:54.333136-05	nndz-WlNlNng3bnhoUT09	4513	t	\N	0	0	0.00		2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
326711	\N	Lauren	Nadler	4572	4339	2025-06-24 19:48:54.333136-05	nndz-WlNlN3hyYjVnZz09	4513	t	\N	0	5	0.00		2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
326712	\N	Lisa	Silver	4572	4339	2025-06-24 19:48:54.333136-05	nndz-WkMrK3lMLy9nUT09	4513	t	\N	1	6	14.30		2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
326713	\N	Jennifer	Stoller	4572	4339	2025-06-24 19:48:54.333136-05	nndz-WlNlN3hiditnUT09	4513	t	\N	1	3	25.00		2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
326714	\N	Lisa	Lord Aronson	4572	4339	2025-06-24 19:48:54.333136-05	nndz-WlNlOXhidjRndz09	4513	t	\N	2	3	40.00		2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
326715	\N	Tracy	Noren	4572	4339	2025-06-24 19:48:54.333136-05	nndz-WkM2eHlicjZnUT09	4513	t	\N	0	2	0.00		2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
326716	\N	Ella	Flusser	4580	4339	2025-06-24 19:48:54.333136-05	nndz-WlNlNnhyMy9qQT09	4513	t	\N	5	4	55.60	C	2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
326717	\N	David	Pollack	4580	4339	2025-06-24 19:48:54.333136-05	nndz-WlNlNnhyNzRnZz09	4513	t	\N	0	0	0.00	CC	2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
326718	\N	Joanna	Davidson	4580	4339	2025-06-24 19:48:54.333136-05	nndz-WkMrK3hidjVoUT09	4513	t	\N	1	1	50.00		2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
326719	\N	Sondra	Douglass	4580	4339	2025-06-24 19:48:54.333136-05	nndz-WkMrK3liNzhnQT09	4513	t	\N	2	2	50.00		2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
326720	\N	Rae	Gruetzmacher	4580	4339	2025-06-24 19:48:54.333136-05	nndz-WlNlN3hiYjloZz09	4513	t	\N	6	7	46.20		2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
326721	\N	Natalie	Kapnick	4580	4339	2025-06-24 19:48:54.333136-05	nndz-WkM2eHhyLzlqUT09	4513	t	\N	0	1	0.00		2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
326722	\N	Melanie	Manning	4580	4339	2025-06-24 19:48:54.333136-05	nndz-WlNhL3dyditnQT09	4513	t	\N	0	0	0.00		2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
326723	\N	Audrey	Margol	4580	4339	2025-06-24 19:48:54.333136-05	nndz-WkM2eHhyLzhodz09	4513	t	\N	4	5	44.40		2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
326724	\N	Margaret	McIntire	4580	4339	2025-06-24 19:48:54.333136-05	nndz-WlNlNnlMai9qUT09	4513	t	\N	0	0	0.00		2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
326725	\N	Brenda	Robles	4580	4339	2025-06-24 19:48:54.333136-05	nndz-WkMreHdiZjZnUT09	4513	t	\N	3	5	37.50		2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
326726	\N	Kathleen	Weaver	4580	4339	2025-06-24 19:48:54.333136-05	nndz-WkM2eHhyLzloUT09	4513	t	\N	1	4	20.00		2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
326727	\N	Maggie	Abramson	4580	4339	2025-06-24 19:48:54.333136-05	nndz-WkM2eHhyLzdnQT09	4513	t	\N	0	0	0.00		2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
326728	\N	Kristin	Barber	4580	4339	2025-06-24 19:48:54.333136-05	nndz-WkMreHliLzlndz09	4513	t	\N	0	0	0.00		2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
326729	\N	Caitlin	Bourne	4580	4339	2025-06-24 19:48:54.333136-05	nndz-WlNlNnhyMy9oZz09	4513	t	\N	11	0	100.00		2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
326730	\N	Christine	Dion	4580	4339	2025-06-24 19:48:54.333136-05	nndz-WkNHNXg3LzRnZz09	4513	t	\N	0	0	0.00		2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
326731	\N	Allyson	Dobbins	4580	4339	2025-06-24 19:48:54.333136-05	nndz-WkMrK3hiejloZz09	4513	t	\N	3	3	50.00		2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
326732	\N	Emily	Doron	4580	4339	2025-06-24 19:48:54.333136-05	nndz-WlNlNnhMYjVqUT09	4513	t	\N	10	1	90.90		2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
326733	\N	Poonum	Doshi	4580	4339	2025-06-24 19:48:54.333136-05	nndz-WlNhNndiNzhnUT09	4513	t	\N	0	0	0.00		2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
326734	\N	Catherine	Ernst	4580	4339	2025-06-24 19:48:54.333136-05	nndz-WkM2eHhyLzdqQT09	4513	t	\N	0	0	0.00		2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
326735	\N	Christine	Ipema	4580	4339	2025-06-24 19:48:54.333136-05	nndz-WkM2eHhyLzlnZz09	4513	t	\N	6	1	85.70		2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
326736	\N	Mary	Clare Kadison	4580	4339	2025-06-24 19:48:54.333136-05	nndz-WlNhNnhiLzloQT09	4513	t	\N	8	2	80.00		2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
326737	\N	Michelle	Kaylor	4580	4339	2025-06-24 19:48:54.333136-05	nndz-WkMrK3hiejRnZz09	4513	t	\N	5	3	62.50		2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
326738	\N	Kacey	Koessl	4580	4339	2025-06-24 19:48:54.333136-05	nndz-WkMreHhyejhnQT09	4513	t	\N	9	0	100.00		2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
326739	\N	Wendy	Laesch	4580	4339	2025-06-24 19:48:54.333136-05	nndz-WkMrK3dMcjRoZz09	4513	t	\N	6	3	66.70		2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
326740	\N	Katie	McQuarrie	4580	4339	2025-06-24 19:48:54.333136-05	nndz-WkMrK3dyMzVnUT09	4513	t	\N	0	0	0.00		2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
326741	\N	Ashley	Mintz	4580	4339	2025-06-24 19:48:54.333136-05	nndz-WkMrK3dyejZoQT09	4513	t	\N	5	1	83.30		2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
326742	\N	Alissa	Morton	4580	4339	2025-06-24 19:48:54.333136-05	nndz-WlNlN3g3Mzlodz09	4513	t	\N	3	3	50.00		2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
326743	\N	Jaclyn	Penar	4580	4339	2025-06-24 19:48:54.333136-05	nndz-WkMrK3lidi9qQT09	4513	t	\N	9	1	90.00		2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
326744	\N	Lindsay	Utts	4580	4339	2025-06-24 19:48:54.333136-05	nndz-WlNhNnlMMzZoUT09	4513	t	\N	7	1	87.50		2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
326745	\N	Erin	Wilson	4580	4339	2025-06-24 19:48:54.333136-05	nndz-WlNlNnliZjVnQT09	4513	t	\N	2	4	33.30		2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
326746	\N	Hilleri	Zander	4580	4339	2025-06-24 19:48:54.333136-05	nndz-WkNDK3hMZnhodz09	4513	t	\N	0	0	0.00		2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
326747	\N	Maro	Zrike	4580	4339	2025-06-24 19:48:54.333136-05	nndz-WkM2eHhyLy9oZz09	4513	t	\N	6	3	66.70		2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
326748	\N	Shanley	Henry	4585	4339	2025-06-24 19:48:54.333136-05	nndz-WkMrK3hMLzZoUT09	4513	t	\N	9	5	64.30	C	2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
326749	\N	Debra	Beck	4585	4339	2025-06-24 19:48:54.333136-05	nndz-WlNlNng3anhqQT09	4513	t	\N	1	1	50.00		2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
326750	\N	Tracy	Cahillane	4585	4339	2025-06-24 19:48:54.333136-05	nndz-WkMrK3lMejdnZz09	4513	t	\N	0	0	0.00		2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
326751	\N	kathy	carlstsrom	4585	4339	2025-06-24 19:48:54.333136-05	nndz-WlNlNnlMYnhqUT09	4513	t	\N	2	3	40.00		2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
326752	\N	kathleen	duda	4585	4339	2025-06-24 19:48:54.333136-05	nndz-WlNlL3hyZjZodz09	4513	t	\N	0	1	0.00		2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
326753	\N	Emery	McCrory	4585	4339	2025-06-24 19:48:54.333136-05	nndz-WlNlOXhibitndz09	4513	t	\N	4	3	57.10		2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
326754	\N	Mary	Oelerich	4585	4339	2025-06-24 19:48:54.333136-05	nndz-WkM2eHg3ajZnZz09	4513	t	\N	0	0	0.00		2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
326755	\N	Samantha	Schwalm	4585	4339	2025-06-24 19:48:54.333136-05	nndz-WlNlOXdieitoQT09	4513	t	\N	6	0	100.00		2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
326756	\N	Karen	Slimmon	4585	4339	2025-06-24 19:48:54.333136-05	nndz-WlNlOXhiNzVndz09	4513	t	\N	6	1	85.70		2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
326757	\N	Julie	Winship	4585	4339	2025-06-24 19:48:54.333136-05	nndz-WlNlNndybjVnQT09	4513	t	\N	0	0	0.00		2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
326758	\N	Lisa	Grady	4585	4339	2025-06-24 19:48:54.333136-05	nndz-WlNlNnlMejlndz09	4513	t	\N	4	3	57.10		2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
326759	\N	Eliza	Holstein	4585	4339	2025-06-24 19:48:54.333136-05	nndz-WkMrK3lMNzRnQT09	4513	t	\N	4	4	50.00		2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
326760	\N	Molly	Chandler	4585	4339	2025-06-24 19:48:54.333136-05	nndz-WkM2eHhyLy9nZz09	4513	t	\N	6	1	85.70		2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
326761	\N	Eileen	Douglass	4585	4339	2025-06-24 19:48:54.333136-05	nndz-WkM2eHlMMzlnQT09	4513	t	\N	3	2	60.00		2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
326762	\N	Jenny	Duda	4585	4339	2025-06-24 19:48:54.333136-05	nndz-WkM2eHhyLytoUT09	4513	t	\N	7	3	70.00		2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
326763	\N	Caroline	Kinahan	4585	4339	2025-06-24 19:48:54.333136-05	nndz-WkM2eHhyLytnQT09	4513	t	\N	12	1	92.30		2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
326764	\N	Sally	McCann	4585	4339	2025-06-24 19:48:54.333136-05	nndz-WlNlN3liNytnQT09	4513	t	\N	6	3	66.70		2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
326765	\N	Madelyn	Nigh	4585	4339	2025-06-24 19:48:54.333136-05	nndz-WlNhNnliLy9nUT09	4513	t	\N	7	1	87.50		2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
326766	\N	Michelle	Podorsky	4585	4339	2025-06-24 19:48:54.333136-05	nndz-WkM2eHlMbjdqQT09	4513	t	\N	8	3	72.70		2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
326767	\N	Elizabeth	Schlatter	4585	4339	2025-06-24 19:48:54.333136-05	nndz-WkM2eHhyLytqUT09	4513	t	\N	1	5	16.70		2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
326768	\N	Liz	Thompson	4585	4339	2025-06-24 19:48:54.333136-05	nndz-WkMrK3liZndodz09	4513	t	\N	9	1	90.00		2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
326769	\N	Susan	Walsh	4585	4339	2025-06-24 19:48:54.333136-05	nndz-WkM2eHhyL3hoUT09	4513	t	\N	1	0	100.00		2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
326770	\N	Kelly	Woodbury	4585	4339	2025-06-24 19:48:54.333136-05	nndz-WlNlN3liNzVndz09	4513	t	\N	4	3	57.10		2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
326771	\N	Mary	Kelly Birkmeier	4599	4339	2025-06-24 19:48:54.333136-05	nndz-WlNlN3dMei9nZz09	4513	t	\N	4	2	66.70	C	2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
326772	\N	Katia	Casademunt	4599	4339	2025-06-24 19:48:54.333136-05	nndz-WkM2eHhyei9qQT09	4513	t	\N	0	1	0.00		2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
326773	\N	Nicole	Elliott	4599	4339	2025-06-24 19:48:54.333136-05	nndz-WlNlNnhiYnhoUT09	4513	t	\N	5	1	83.30		2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
326774	\N	Christine	Everett	4599	4339	2025-06-24 19:48:54.333136-05	nndz-WlNlN3dMLzlnUT09	4513	t	\N	1	6	14.30		2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
326775	\N	Kate	Galloway	4599	4339	2025-06-24 19:48:54.333136-05	nndz-WlNlNnhMbjhqQT09	4513	t	\N	2	3	40.00		2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
326776	\N	theresa	hoffmann	4599	4339	2025-06-24 19:48:54.333136-05	nndz-WkMrK3lMbndoZz09	4513	t	\N	5	4	55.60		2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
326777	\N	Kristin	MacCarthy	4599	4339	2025-06-24 19:48:54.333136-05	nndz-WlNlOXg3MzRqUT09	4513	t	\N	3	1	75.00		2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
326778	\N	Adrienne	Murrill	4599	4339	2025-06-24 19:48:54.333136-05	nndz-WkM2d3hMei9qQT09	4513	t	\N	2	2	50.00		2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
326779	\N	Ann	Marie Nedeau	4599	4339	2025-06-24 19:48:54.333136-05	nndz-WlNlOXhyZnhqUT09	4513	t	\N	3	1	75.00		2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
326780	\N	Vanessa	Poulton	4599	4339	2025-06-24 19:48:54.333136-05	nndz-WlNlN3hiYi9nQT09	4513	t	\N	1	4	20.00		2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
326781	\N	Piper	Schlafly	4599	4339	2025-06-24 19:48:54.333136-05	nndz-WlNlOXhyZndoUT09	4513	t	\N	3	2	60.00		2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
326782	\N	Simi	Chhabria	4599	4339	2025-06-24 19:48:54.333136-05	nndz-WlNlN3c3bndoQT09	4513	t	\N	4	5	44.40		2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
326783	\N	Marci	Graham	4599	4339	2025-06-24 19:48:54.333136-05	nndz-WkMreHdMLzZoQT09	4513	t	\N	5	2	71.40		2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
326784	\N	Britta	Johnson	4599	4339	2025-06-24 19:48:54.333136-05	nndz-WlNlNng3cjRqQT09	4513	t	\N	7	1	87.50		2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
326785	\N	Tiffany	Olson	4599	4339	2025-06-24 19:48:54.333136-05	nndz-WkMreHdyM3hoQT09	4513	t	\N	4	4	50.00		2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
326786	\N	Carrie	Tracy	4599	4339	2025-06-24 19:48:54.333136-05	nndz-WlNlN3libjdndz09	4513	t	\N	5	4	55.60		2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
326787	\N	Jordan	Daul	4611	4339	2025-06-24 19:48:54.333136-05	nndz-WkM2eHhycjhnQT09	4513	t	\N	1	4	20.00	C	2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
326788	\N	Taylor	Kehoe	4611	4339	2025-06-24 19:48:54.333136-05	nndz-WkMrL3lMLzlodz09	4513	t	\N	3	4	42.90	CC	2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
326789	\N	Heather	Andrikanich	4611	4339	2025-06-24 19:48:54.333136-05	nndz-WkM2d3c3cndndz09	4513	t	\N	0	0	0.00		2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
326790	\N	Natalie	Elena Cappiello	4611	4339	2025-06-24 19:48:54.333136-05	nndz-WkMrL3lMLzZnZz09	4513	t	\N	2	2	50.00		2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
326791	\N	Jessica	Fahey	4611	4339	2025-06-24 19:48:54.333136-05	nndz-WkMrL3lMLzhoQT09	4513	t	\N	1	2	33.30		2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
326792	\N	Lizbeth	Keefe	4611	4339	2025-06-24 19:48:54.333136-05	nndz-WkMrK3diejlodz09	4513	t	\N	0	3	0.00		2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
326793	\N	Jillian	Lose	4611	4339	2025-06-24 19:48:54.333136-05	nndz-WkMrL3lMLzloQT09	4513	t	\N	1	3	25.00		2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
326794	\N	McKenna	McNamara	4611	4339	2025-06-24 19:48:54.333136-05	nndz-WlNlOHhiajRnQT09	4513	t	\N	1	4	20.00		2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
326795	\N	Cameron	Park	4611	4339	2025-06-24 19:48:54.333136-05	nndz-WlNlN3dML3dnZz09	4513	t	\N	1	5	16.70		2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
326796	\N	Aidan	Reedy	4611	4339	2025-06-24 19:48:54.333136-05	nndz-WkM2eHhyci9oZz09	4513	t	\N	2	7	22.20		2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
326797	\N	Katie	Santucci	4611	4339	2025-06-24 19:48:54.333136-05	nndz-WkM2eHhyci9nUT09	4513	t	\N	2	4	33.30		2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
326798	\N	Jackie	Scoby	4611	4339	2025-06-24 19:48:54.333136-05	nndz-WkMrK3diNytoQT09	4513	t	\N	2	2	50.00		2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
326799	\N	Emily	Kortz	4611	4339	2025-06-24 19:48:54.333136-05	nndz-WlNlOXhMbitoZz09	4513	t	\N	0	1	0.00		2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
326800	\N	Claire	Manning	4611	4339	2025-06-24 19:48:54.333136-05	nndz-WkMreHhMN3doUT09	4513	t	\N	6	1	85.70		2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
326801	\N	AMY	MCCANN	4611	4339	2025-06-24 19:48:54.333136-05	nndz-WkMrK3dybndnUT09	4513	t	\N	6	5	54.50		2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
326802	\N	Claudia	Minner	4611	4339	2025-06-24 19:48:54.333136-05	nndz-WlNlNHliZitodz09	4513	t	\N	4	3	57.10		2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
326803	\N	Martha	Purcell	4611	4339	2025-06-24 19:48:54.333136-05	nndz-WlNlOXhMYjRoUT09	4513	t	\N	4	3	57.10		2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
326804	\N	Meghan	Shanahan	4611	4339	2025-06-24 19:48:54.333136-05	nndz-WkM2d3c3djVqQT09	4513	t	\N	7	1	87.50		2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
326805	\N	Eileen	Thanner	4611	4339	2025-06-24 19:48:54.333136-05	nndz-WlNlN3c3L3hoZz09	4513	t	\N	1	5	16.70		2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
326806	\N	Dana	Trumbull	4611	4339	2025-06-24 19:48:54.333136-05	nndz-WkM2d3c3djRoUT09	4513	t	\N	5	2	71.40		2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
326807	\N	Tracey	Weber	4611	4339	2025-06-24 19:48:54.333136-05	nndz-WlNlL3hyYnhnUT09	4513	t	\N	1	1	50.00		2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
326808	\N	Alexandra	Wilson	4611	4339	2025-06-24 19:48:54.333136-05	nndz-WkMrL3lMNzRoZz09	4513	t	\N	1	5	16.70		2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
326809	\N	Sheila	Metzner	4638	4339	2025-06-24 19:48:54.333136-05	nndz-WkMrK3hMcjlodz09	4513	t	\N	3	7	30.00	C	2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
326810	\N	Jamie	Agay	4638	4339	2025-06-24 19:48:54.333136-05	nndz-WlNlN3dMdjZoQT09	4513	t	\N	5	1	83.30		2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
326811	\N	Kerri	Day	4638	4339	2025-06-24 19:48:54.333136-05	nndz-WkMrL3lMYitnQT09	4513	t	\N	0	3	0.00		2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
326812	\N	Jessica	Freedman	4638	4339	2025-06-24 19:48:54.333136-05	nndz-WkMrK3dMMzdndz09	4513	t	\N	2	4	33.30		2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
326813	\N	Patti	Kalal	4638	4339	2025-06-24 19:48:54.333136-05	nndz-WkNDL3didjhqUT09	4513	t	\N	2	2	50.00		2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
326814	\N	Carly	Lebenson	4638	4339	2025-06-24 19:48:54.333136-05	nndz-WlNlN3dMcjhodz09	4513	t	\N	3	2	60.00		2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
326815	\N	Kathy	McNamara	4638	4339	2025-06-24 19:48:54.333136-05	nndz-WkMrK3c3ZjhqQT09	4513	t	\N	1	7	12.50		2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
326816	\N	Lori	Meagher	4638	4339	2025-06-24 19:48:54.333136-05	nndz-WkM2eHhybjdnZz09	4513	t	\N	0	4	0.00		2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
326817	\N	Gail	Osterman	4638	4339	2025-06-24 19:48:54.333136-05	nndz-WlNlN3dyendnQT09	4513	t	\N	0	5	0.00		2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
326818	\N	Jan	Schwanke	4638	4339	2025-06-24 19:48:54.333136-05	nndz-WkNDL3dici9odz09	4513	t	\N	1	7	12.50		2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
326819	\N	Lori	Schwartz	4638	4339	2025-06-24 19:48:54.333136-05	nndz-WkM2eHhybjdqUT09	4513	t	\N	0	2	0.00		2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
326820	\N	Denise	Siegel	4638	4339	2025-06-24 19:48:54.333136-05	nndz-WkM2eHhybndqUT09	4513	t	\N	6	1	85.70		2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
326821	\N	Audrey	Love	4638	4339	2025-06-24 19:48:54.333136-05	nndz-WkM2eHhybndoZz09	4513	t	\N	2	6	25.00		2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
326822	\N	Andria	Hendricks	4639	4339	2025-06-24 19:48:54.333136-05	nndz-WkM2eHhyYjdqUT09	4513	t	\N	2	3	40.00	C	2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
326823	\N	Sarah	Hayes	4639	4339	2025-06-24 19:48:54.333136-05	nndz-WkM2eHhyYjdndz09	4513	t	\N	4	4	50.00	CC	2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
326824	\N	Ashley	Acuna	4639	4339	2025-06-24 19:48:54.333136-05	nndz-WkMrK3dyajVqQT09	4513	t	\N	4	2	66.70		2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
326825	\N	Alina	Izzo	4639	4339	2025-06-24 19:48:54.333136-05	nndz-WkNDL3dicjZoZz09	4513	t	\N	0	2	0.00		2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
326826	\N	Gail	Silversten	4639	4339	2025-06-24 19:48:54.333136-05	nndz-WkMrK3hiNzdoUT09	4513	t	\N	2	4	33.30		2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
326827	\N	Helen	Skinner	4639	4339	2025-06-24 19:48:54.333136-05	nndz-WkMrN3hyYitndz09	4513	t	\N	3	4	42.90		2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
326828	\N	Barbara	Smith	4639	4339	2025-06-24 19:48:54.333136-05	nndz-WkMrK3dyaitqUT09	4513	t	\N	1	5	16.70		2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
326829	\N	Rachel	True	4639	4339	2025-06-24 19:48:54.333136-05	nndz-WlNlNnhibjZnZz09	4513	t	\N	3	4	42.90		2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
326830	\N	Emily	Martensen	4639	4339	2025-06-24 19:48:54.333136-05	nndz-WkMrK3hiajdoZz09	4513	t	\N	4	4	50.00		2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
326831	\N	Carolyn	Moretti	4639	4339	2025-06-24 19:48:54.333136-05	nndz-WkM2eHhyZjRnZz09	4513	t	\N	6	4	60.00		2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
326832	\N	Tonya	Wheeler	4639	4339	2025-06-24 19:48:54.333136-05	nndz-WkM2eHhyZjVndz09	4513	t	\N	3	6	33.30		2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
326833	\N	Erin	Cook	4639	4339	2025-06-24 19:48:54.333136-05	nndz-WkM2eHhyYi9nQT09	4513	t	\N	6	1	85.70		2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
326834	\N	Beth	Kersten	4639	4339	2025-06-24 19:48:54.333136-05	nndz-WkNDL3diLzRoZz09	4513	t	\N	0	0	0.00		2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
326835	\N	Amanda	Kudrna	4639	4339	2025-06-24 19:48:54.333136-05	nndz-WlNlN3g3cjhnQT09	4513	t	\N	3	3	50.00		2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
326836	\N	Becky	Lofstrom Tausche	4639	4339	2025-06-24 19:48:54.333136-05	nndz-WkM2eHhyZjVoUT09	4513	t	\N	1	7	12.50		2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
326837	\N	Jaspreet	Mantrow	4639	4339	2025-06-24 19:48:54.333136-05	nndz-WkM2eHhyZjRndz09	4513	t	\N	1	4	20.00		2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
326838	\N	Marcia	Masloski	4639	4339	2025-06-24 19:48:54.333136-05	nndz-WkNDL3didjdnZz09	4513	t	\N	0	0	0.00		2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
326839	\N	Tina	Monico	4639	4339	2025-06-24 19:48:54.333136-05	nndz-WkMrN3diZjVqUT09	4513	t	\N	0	0	0.00		2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
326840	\N	Rebecca	Tupuritis	4642	4340	2025-06-24 19:48:54.333136-05	nndz-WkMrK3hydnhndz09	4513	t	\N	3	7	30.00	C	2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
326841	\N	Kate	Bluestein	4642	4340	2025-06-24 19:48:54.333136-05	nndz-WkMrK3hMYjhqUT09	4513	t	\N	2	3	40.00	CC	2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
326842	\N	Michelle	Catenacci	4642	4340	2025-06-24 19:48:54.333136-05	nndz-WlNlNHlMbjdnQT09	4513	t	\N	3	5	37.50		2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
326843	\N	Liz	Fritz	4642	4340	2025-06-24 19:48:54.333136-05	nndz-WlNlOXdienhnUT09	4513	t	\N	3	2	60.00		2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
326844	\N	Mandy	Hartman	4642	4340	2025-06-24 19:48:54.333136-05	nndz-WkMrK3hyanhoZz09	4513	t	\N	3	3	50.00		2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
326845	\N	Ashley	Magda	4642	4340	2025-06-24 19:48:54.333136-05	nndz-WlNlNHlMbndqQT09	4513	t	\N	3	3	50.00		2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
326846	\N	Valerie	Overly	4642	4340	2025-06-24 19:48:54.333136-05	nndz-WkMreHdMLzlqUT09	4513	t	\N	4	2	66.70		2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
326847	\N	Kimberly	Portnoy	4642	4340	2025-06-24 19:48:54.333136-05	nndz-WkMrK3hiNzloZz09	4513	t	\N	3	3	50.00		2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
326848	\N	Kerry	Reeg	4642	4340	2025-06-24 19:48:54.333136-05	nndz-WkMrK3hycjVnZz09	4513	t	\N	4	4	50.00		2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
326849	\N	Kathryn	Schmidt	4642	4340	2025-06-24 19:48:54.333136-05	nndz-WlNlN3dieitoZz09	4513	t	\N	5	1	83.30		2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
326850	\N	Katherine	Stabler	4642	4340	2025-06-24 19:48:54.333136-05	nndz-WkMrK3hydnhodz09	4513	t	\N	3	5	37.50		2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
326851	\N	Connie	Daley	4642	4340	2025-06-24 19:48:54.333136-05	nndz-WlNlN3diNytndz09	4513	t	\N	4	4	50.00		2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
326852	\N	Natalie	Laackman	4642	4340	2025-06-24 19:48:54.333136-05	nndz-WkM2eHliN3dnUT09	4513	t	\N	1	11	8.30		2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
326853	\N	Daliah	Saper	4642	4340	2025-06-24 19:48:54.333136-05	nndz-WlNlL3hiMzlnUT09	4513	t	\N	2	3	40.00		2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
326854	\N	Liz	Sullivan	4642	4340	2025-06-24 19:48:54.333136-05	nndz-WkM2eHliN3dqUT09	4513	t	\N	2	7	22.20		2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
326855	\N	Laura	Wayland	4642	4340	2025-06-24 19:48:54.333136-05	nndz-WkM2eHliN3dqQT09	4513	t	\N	5	10	33.30		2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
326856	\N	Jessica	Garro	4642	4341	2025-06-24 19:48:54.333136-05	nndz-WkMrK3hidjVndz09	4513	t	\N	5	3	62.50	C	2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
326857	\N	Annie	Smith	4642	4341	2025-06-24 19:48:54.333136-05	nndz-WkMrK3hidjZnZz09	4513	t	\N	12	1	92.30	CC	2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
326858	\N	Courtney	Beagen	4642	4341	2025-06-24 19:48:54.333136-05	nndz-WkMrK3lMYjZoUT09	4513	t	\N	0	0	0.00		2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
326859	\N	Kathryn	Birch	4642	4341	2025-06-24 19:48:54.333136-05	nndz-WlNlNHlMZjRqQT09	4513	t	\N	6	5	54.50		2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
326860	\N	Maggie	Burke	4642	4341	2025-06-24 19:48:54.333136-05	nndz-WkMreHdMLzVqQT09	4513	t	\N	13	1	92.90		2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
326861	\N	Sheila	Byrnes	4642	4341	2025-06-24 19:48:54.333136-05	nndz-WlNhL3liZjVoZz09	4513	t	\N	6	1	85.70		2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
326862	\N	Kelly	Cox	4642	4341	2025-06-24 19:48:54.333136-05	nndz-WlNlN3g3L3doQT09	4513	t	\N	0	0	0.00		2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
326863	\N	Elizabeth	Crouch	4642	4341	2025-06-24 19:48:54.333136-05	nndz-WkMreHdMLzRnUT09	4513	t	\N	3	8	27.30		2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
326864	\N	Kristen	Kwasnick	4642	4341	2025-06-24 19:48:54.333136-05	nndz-WlNlNnhiNy9oZz09	4513	t	\N	5	4	55.60		2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
326865	\N	Courtney	Phillips	4642	4341	2025-06-24 19:48:54.333136-05	nndz-WkMreHdiN3hnZz09	4513	t	\N	2	1	66.70		2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
326866	\N	Julianna	Salvi	4642	4341	2025-06-24 19:48:54.333136-05	nndz-WlNlOXdyenhoZz09	4513	t	\N	6	6	50.00		2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
326867	\N	Abby	Shek	4642	4341	2025-06-24 19:48:54.333136-05	nndz-WlNlOHlMdjhnUT09	4513	t	\N	3	3	50.00		2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
326868	\N	Connie	Daley	4642	4341	2025-06-24 19:48:54.333136-05	nndz-WlNlN3diNytndz09	4513	t	\N	4	4	50.00		2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
326869	\N	Corey	Darnieder	4642	4341	2025-06-24 19:48:54.333136-05	nndz-WlNlNng3di9qUT09	4513	t	\N	2	4	33.30		2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
326870	\N	Beth	Mark	4642	4341	2025-06-24 19:48:54.333136-05	nndz-WlNlNng3Ly9oQT09	4513	t	\N	5	3	62.50		2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
326871	\N	Anna	Panici	4642	4341	2025-06-24 19:48:54.333136-05	nndz-WlNlL3diNzhodz09	4513	t	\N	5	4	55.60		2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
326872	\N	Anna	Petric	4642	4341	2025-06-24 19:48:54.333136-05	nndz-WlNlN3diejRoUT09	4513	t	\N	8	3	72.70		2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
326873	\N	Danielle	Walsh	4646	4339	2025-06-24 19:48:54.333136-05	nndz-WlNlN3c3cjdoZz09	4513	t	\N	4	4	50.00	C	2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
326874	\N	Casey	Thibeault	4646	4339	2025-06-24 19:48:54.333136-05	nndz-WlNlN3liajhoQT09	4513	t	\N	3	4	42.90	CC	2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
326875	\N	Molly	Boehm	4646	4339	2025-06-24 19:48:54.333136-05	nndz-WkM2eHhyejVndz09	4513	t	\N	4	3	57.10		2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
326876	\N	Mariana	Dalto	4646	4339	2025-06-24 19:48:54.333136-05	nndz-WlNlN3dycjhodz09	4513	t	\N	0	0	0.00		2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
326877	\N	Carey	Elder	4646	4339	2025-06-24 19:48:54.333136-05	nndz-WlNlN3g3enhnQT09	4513	t	\N	5	1	83.30		2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
326878	\N	Julie	Feiten	4646	4339	2025-06-24 19:48:54.333136-05	nndz-WlNlN3hiYitoZz09	4513	t	\N	7	1	87.50		2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
326879	\N	Jennifer	Lerum	4646	4339	2025-06-24 19:48:54.333136-05	nndz-WlNlNng3ditnUT09	4513	t	\N	3	2	60.00		2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
326880	\N	Michelle	Meltzer	4646	4339	2025-06-24 19:48:54.333136-05	nndz-WlNlNng3andndz09	4513	t	\N	1	5	16.70		2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
326881	\N	Dana	Snyder	4646	4339	2025-06-24 19:48:54.333136-05	nndz-WlNlN3hiajVoUT09	4513	t	\N	1	4	20.00		2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
326882	\N	Julie	Zemon	4646	4339	2025-06-24 19:48:54.333136-05	nndz-WlNlN3dyMzdoZz09	4513	t	\N	2	3	40.00		2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
326883	\N	Sofia	Becker	4646	4339	2025-06-24 19:48:54.333136-05	nndz-WlNlN3dyMzhoUT09	4513	t	\N	1	5	16.70		2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
326884	\N	Meredith	Goodspeed	4646	4339	2025-06-24 19:48:54.333136-05	nndz-WlNlN3diZjlodz09	4513	t	\N	7	2	77.80		2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
326885	\N	Emma	Khoury	4646	4339	2025-06-24 19:48:54.333136-05	nndz-WlNlN3hiMzVqQT09	4513	t	\N	6	4	60.00		2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
326886	\N	Sarah	Matteson	4646	4339	2025-06-24 19:48:54.333136-05	nndz-WkMrL3lMajVoQT09	4513	t	\N	0	6	0.00		2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
326887	\N	Theresa	Rose	4646	4339	2025-06-24 19:48:54.333136-05	nndz-WkMrL3lMZjRnZz09	4513	t	\N	1	5	16.70		2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
326888	\N	Corey	Sharkey	4646	4339	2025-06-24 19:48:54.333136-05	nndz-WlNlN3dMbitnZz09	4513	t	\N	0	7	0.00		2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
326889	\N	Sarah	Tanham	4646	4339	2025-06-24 19:48:54.333136-05	nndz-WlNlL3g3ajZoZz09	4513	t	\N	0	1	0.00		2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
326890	\N	Emily	Webber	4646	4339	2025-06-24 19:48:54.333136-05	nndz-WkMrK3diL3hqUT09	4513	t	\N	4	4	50.00		2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
326891	\N	Annie	Tarkington	4646	4339	2025-06-24 19:48:54.333136-05	nndz-WlNlN3c3cnhnQT09	4513	t	\N	2	4	33.30		2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
326892	\N	Libby	Carlson	4579	4342	2025-06-24 19:48:54.333136-05	nndz-WkMrK3dyLy9oZz09	4513	t	\N	2	3	40.00	C	2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
326893	\N	Cassidy	Duvall	4579	4342	2025-06-24 19:48:54.333136-05	nndz-WkMrL3lMNzVqQT09	4513	t	\N	2	1	66.70	CC	2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
326894	\N	Laura	Butts	4579	4342	2025-06-24 19:48:54.333136-05	nndz-WlNlN3dMNzhodz09	4513	t	\N	2	2	50.00		2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
326895	\N	Natalie	Davis	4579	4342	2025-06-24 19:48:54.333136-05	nndz-WkMrK3dyLy9nQT09	4513	t	\N	2	2	50.00		2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
326896	\N	Linda	Hauser	4579	4342	2025-06-24 19:48:54.333136-05	nndz-WkM2eHhyNy9oQT09	4513	t	\N	0	3	0.00		2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
326897	\N	Danielle	Hoeg	4579	4342	2025-06-24 19:48:54.333136-05	nndz-WlNhNnhyLzloQT09	4513	t	\N	0	5	0.00		2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
326898	\N	Lizzie	Hoffman	4579	4342	2025-06-24 19:48:54.333136-05	nndz-WlNlN3diNzlqUT09	4513	t	\N	2	1	66.70		2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
326899	\N	Jentry	Jordan	4579	4342	2025-06-24 19:48:54.333136-05	nndz-WkM2eHhyN3hnQT09	4513	t	\N	4	1	80.00		2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
326900	\N	Sascha	Kalpake	4579	4342	2025-06-24 19:48:54.333136-05	nndz-WkMreHc3ZjlqQT09	4513	t	\N	2	2	50.00		2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
326901	\N	Jen	Lunt	4579	4342	2025-06-24 19:48:54.333136-05	nndz-WkM2eHhyNy9nUT09	4513	t	\N	2	4	33.30		2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
326902	\N	Robin	Velo	4579	4342	2025-06-24 19:48:54.333136-05	nndz-WkMrK3lMNzhoZz09	4513	t	\N	0	2	0.00		2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
326903	\N	Heather	Shaffer	4579	4342	2025-06-24 19:48:54.333136-05	nndz-WlNlN3diNzhoUT09	4513	t	\N	3	4	42.90		2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
326904	\N	Anne	Sullivan	4579	4342	2025-06-24 19:48:54.333136-05	nndz-WlNlN3diNzlqQT09	4513	t	\N	3	0	100.00		2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
326905	\N	Ashley	Gauntlett	4579	4342	2025-06-24 19:48:54.333136-05	nndz-WkMrK3dyLy9ndz09	4513	t	\N	0	0	0.00		2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
326906	\N	Margaret	LeFevour	4579	4342	2025-06-24 19:48:54.333136-05	nndz-WkMrK3diZitoUT09	4513	t	\N	2	4	33.30		2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
326907	\N	Lesly	Levitas	4579	4342	2025-06-24 19:48:54.333136-05	nndz-WkMrK3dyLy9qUT09	4513	t	\N	0	0	0.00		2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
326908	\N	Julie	Lynk	4579	4342	2025-06-24 19:48:54.333136-05	nndz-WkMrK3dMMy9nZz09	4513	t	\N	0	0	0.00		2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
326909	\N	Katie	McCormack	4579	4342	2025-06-24 19:48:54.333136-05	nndz-WlNlN3lMNzVnQT09	4513	t	\N	0	0	0.00		2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
326910	\N	Erin	McGinn	4579	4342	2025-06-24 19:48:54.333136-05	nndz-WkMreHdMZjZnZz09	4513	t	\N	0	0	0.00		2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
326911	\N	Solita	Murphy	4579	4342	2025-06-24 19:48:54.333136-05	nndz-WkMrNndiZjhqQT09	4513	t	\N	0	0	0.00		2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
326912	\N	Ana	Pescatello	4579	4342	2025-06-24 19:48:54.333136-05	nndz-WlNlN3lMNzVndz09	4513	t	\N	0	0	0.00		2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
326913	\N	Jeni	Roderick	4579	4342	2025-06-24 19:48:54.333136-05	nndz-WkMrK3dyMzRqUT09	4513	t	\N	0	0	0.00		2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
326914	\N	Tracy	Petersen Kasniunas	4608	4342	2025-06-24 19:48:54.333136-05	nndz-WkMrL3lMMytnQT09	4513	t	\N	4	4	50.00	C	2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
326915	\N	Julie	Luby	4608	4342	2025-06-24 19:48:54.333136-05	nndz-WkMrL3lMMytqQT09	4513	t	\N	3	2	60.00	CC	2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
326916	\N	Ann	Dronen	4608	4342	2025-06-24 19:48:54.333136-05	nndz-WkMrL3lMMytoQT09	4513	t	\N	1	2	33.30		2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
326917	\N	Joy	Harrison	4608	4342	2025-06-24 19:48:54.333136-05	nndz-WlNlN3dMNzVndz09	4513	t	\N	2	4	33.30		2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
326918	\N	Kelli	Johnson	4608	4342	2025-06-24 19:48:54.333136-05	nndz-WlNlN3dMNzVnZz09	4513	t	\N	6	4	60.00		2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
326919	\N	Donley	Klug	4608	4342	2025-06-24 19:48:54.333136-05	nndz-WkMreHdiNzRnZz09	4513	t	\N	2	7	22.20		2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
326920	\N	Annie	Rogers	4608	4342	2025-06-24 19:48:54.333136-05	nndz-WkM2eHhycjZnZz09	4513	t	\N	1	3	25.00		2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
326921	\N	Elizabeth	Roussil	4608	4342	2025-06-24 19:48:54.333136-05	nndz-WlNlN3diZjhnQT09	4513	t	\N	4	3	57.10		2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
326922	\N	Rebecca	Snellenbarger	4608	4342	2025-06-24 19:48:54.333136-05	nndz-WkMreHhML3hnZz09	4513	t	\N	5	1	83.30		2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
326923	\N	Colleen	Summe	4608	4342	2025-06-24 19:48:54.333136-05	nndz-WlNlN3dMNzVqQT09	4513	t	\N	5	1	83.30		2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
326924	\N	Jo	Anne Tagliamonte	4608	4342	2025-06-24 19:48:54.333136-05	nndz-WkMreHdiZjZqUT09	4513	t	\N	2	2	50.00		2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
326925	\N	Carly	Cook	4608	4342	2025-06-24 19:48:54.333136-05	nndz-WkMrL3lMejRodz09	4513	t	\N	5	4	55.60		2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
326926	\N	Amanda	Hollis	4608	4342	2025-06-24 19:48:54.333136-05	nndz-WkMrK3diZi9nZz09	4513	t	\N	8	5	61.50		2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
326927	\N	Laura	Leber	4608	4342	2025-06-24 19:48:54.333136-05	nndz-WkM2eHhycjRqUT09	4513	t	\N	7	0	100.00		2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
326928	\N	Markell	Smith	4608	4342	2025-06-24 19:48:54.333136-05	nndz-WkM2eHhycjdnQT09	4513	t	\N	8	0	100.00		2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
326929	\N	Caoilfhionn	Hannon	4618	4342	2025-06-24 19:48:54.333136-05	nndz-WkMrK3dMN3dqUT09	4513	t	\N	3	4	42.90	C	2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
326930	\N	Lynora	Dobry	4618	4342	2025-06-24 19:48:54.333136-05	nndz-WkMrK3c3Yjhodz09	4513	t	\N	6	0	100.00	CC	2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
326931	\N	Julie	Barry	4618	4342	2025-06-24 19:48:54.333136-05	nndz-WkM2eHhydjVoZz09	4513	t	\N	2	3	40.00		2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
326932	\N	Kara	Callero	4618	4342	2025-06-24 19:48:54.333136-05	nndz-WlNlN3dyYjdoUT09	4513	t	\N	2	1	66.70		2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
326933	\N	Nicole	Dellaringa	4618	4342	2025-06-24 19:48:54.333136-05	nndz-WkNDL3dicjdqQT09	4513	t	\N	3	2	60.00		2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
326934	\N	Susan	DiFranco	4618	4342	2025-06-24 19:48:54.333136-05	nndz-WlNlN3dycjloZz09	4513	t	\N	4	4	50.00		2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
326935	\N	Nicolette	Grieco-Sweet	4618	4342	2025-06-24 19:48:54.333136-05	nndz-WkMrL3lMYi9oQT09	4513	t	\N	0	0	0.00		2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
326936	\N	Flo	Kiokemeister	4618	4342	2025-06-24 19:48:54.333136-05	nndz-WkNDL3didjloUT09	4513	t	\N	0	1	0.00		2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
326937	\N	Katrina	Martin	4618	4342	2025-06-24 19:48:54.333136-05	nndz-WkMrK3dMN3dnZz09	4513	t	\N	1	0	100.00		2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
326938	\N	Jasmina	Pedi	4618	4342	2025-06-24 19:48:54.333136-05	nndz-WlNlN3hidi9qQT09	4513	t	\N	1	2	33.30		2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
326939	\N	Chrissy	Romano	4618	4342	2025-06-24 19:48:54.333136-05	nndz-WkM2eHg3ai9oQT09	4513	t	\N	1	2	33.30		2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
326940	\N	Michele	Svachula	4618	4342	2025-06-24 19:48:54.333136-05	nndz-WkMrK3hiYjhodz09	4513	t	\N	0	0	0.00		2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
326941	\N	Christina	Cosgrove	4618	4342	2025-06-24 19:48:54.333136-05	nndz-WlNhOXhiYjZnZz09	4513	t	\N	0	0	0.00		2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
326942	\N	Amanda	Rafferty	4618	4342	2025-06-24 19:48:54.333136-05	nndz-WkNHNXdyNytoZz09	4513	t	\N	2	5	28.60		2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
326943	\N	Michelle	Baumann	4618	4342	2025-06-24 19:48:54.333136-05	nndz-WlNlN3hyNzZqUT09	4513	t	\N	5	2	71.40		2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
326944	\N	ciara	bochenek	4618	4342	2025-06-24 19:48:54.333136-05	nndz-WkMrK3diaitqUT09	4513	t	\N	2	6	25.00		2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
326945	\N	Tiffany	Braun	4618	4342	2025-06-24 19:48:54.333136-05	nndz-WkMrK3dibnhoUT09	4513	t	\N	2	2	50.00		2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
326946	\N	Sara	McDermott	4618	4342	2025-06-24 19:48:54.333136-05	nndz-WkMrK3c3NzVqUT09	4513	t	\N	4	0	100.00		2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
326947	\N	Sarah	McGurn	4618	4342	2025-06-24 19:48:54.333136-05	nndz-WlNlN3hiajlndz09	4513	t	\N	2	3	40.00		2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
326948	\N	Meg	Strotman	4618	4342	2025-06-24 19:48:54.333136-05	nndz-WlNlN3hidnhnQT09	4513	t	\N	3	2	60.00		2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
326949	\N	Melanie	Turner	4618	4342	2025-06-24 19:48:54.333136-05	nndz-WkM2eHhydjRndz09	4513	t	\N	2	1	66.70		2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
326950	\N	Anna	Panici	4642	4342	2025-06-24 19:48:54.333136-05	nndz-WlNlL3diNzhodz09	4513	t	\N	5	4	55.60	C	2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
326951	\N	Meghan	Panici	4642	4342	2025-06-24 19:48:54.333136-05	nndz-WlNlOHlMcjZnUT09	4513	t	\N	3	4	42.90	CC	2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
326952	\N	Joan	V. Angelov	4642	4342	2025-06-24 19:48:54.333136-05	nndz-WlNlL3diMzloZz09	4513	t	\N	1	1	50.00		2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
326953	\N	Hope	Baker	4642	4342	2025-06-24 19:48:54.333136-05	nndz-WlNlL3diMzdndz09	4513	t	\N	0	0	0.00		2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
326954	\N	Emily	D'Souza	4642	4342	2025-06-24 19:48:54.333136-05	nndz-WlNlOHlMLytnUT09	4513	t	\N	1	3	25.00		2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
326955	\N	Kerry	Devine	4642	4342	2025-06-24 19:48:54.333136-05	nndz-WlNlOHlMbjhqQT09	4513	t	\N	3	3	50.00		2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
326956	\N	Marisa	Ellis	4642	4342	2025-06-24 19:48:54.333136-05	nndz-WlNlOHlMMzRnZz09	4513	t	\N	1	2	33.30		2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
326957	\N	Eileen	Hubert	4642	4342	2025-06-24 19:48:54.333136-05	nndz-WlNlL3diM3dodz09	4513	t	\N	4	1	80.00		2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
326958	\N	Amy	Krutky	4642	4342	2025-06-24 19:48:54.333136-05	nndz-WlNlOHlMandoUT09	4513	t	\N	3	1	75.00		2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
326959	\N	Lisa	Rees	4642	4342	2025-06-24 19:48:54.333136-05	nndz-WlNlOHhMajRqQT09	4513	t	\N	4	0	100.00		2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
326960	\N	Lauren	Rudowsky	4642	4342	2025-06-24 19:48:54.333136-05	nndz-WlNlOHhyei9nZz09	4513	t	\N	5	1	83.30		2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
326961	\N	Morgan	Ruey	4642	4342	2025-06-24 19:48:54.333136-05	nndz-WlNlL3diNzVoZz09	4513	t	\N	2	3	40.00		2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
326962	\N	Katy	Vennum	4642	4342	2025-06-24 19:48:54.333136-05	nndz-WlNlOHlibnhoQT09	4513	t	\N	5	0	100.00		2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
326963	\N	Beth	Mark	4642	4342	2025-06-24 19:48:54.333136-05	nndz-WlNlNng3Ly9oQT09	4513	t	\N	5	3	62.50		2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
326964	\N	Claire	Concannon	4649	4342	2025-06-24 19:48:54.333136-05	nndz-WkM2eHhyMytoUT09	4513	t	\N	2	3	40.00	C	2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
326965	\N	Anna	O'Connor	4649	4342	2025-06-24 19:48:54.333136-05	nndz-WkM2eHhyMy9nUT09	4513	t	\N	2	1	66.70	CC	2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
326966	\N	Kate	Adamany	4649	4342	2025-06-24 19:48:54.333136-05	nndz-WlNlOXdMLzhndz09	4513	t	\N	0	0	0.00		2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
326967	\N	Alexis	Beckley	4649	4342	2025-06-24 19:48:54.333136-05	nndz-WlNlNnhyN3dnZz09	4513	t	\N	0	0	0.00		2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
326968	\N	Kristen	Boettcher	4649	4342	2025-06-24 19:48:54.333136-05	nndz-WlNlNnhyNytqUT09	4513	t	\N	2	2	50.00		2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
326969	\N	Jamie	Cruz	4649	4342	2025-06-24 19:48:54.333136-05	nndz-WkMrL3lMci9qUT09	4513	t	\N	1	1	50.00		2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
326970	\N	Emily	Delfino	4649	4342	2025-06-24 19:48:54.333136-05	nndz-WlNlOXdMMzdnZz09	4513	t	\N	0	2	0.00		2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
326971	\N	Kristan	Griesbach	4649	4342	2025-06-24 19:48:54.333136-05	nndz-WlNlNnhyNy9oZz09	4513	t	\N	1	5	16.70		2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
326972	\N	Alyssa	Hopkins	4649	4342	2025-06-24 19:48:54.333136-05	nndz-WkMrK3hMajloZz09	4513	t	\N	0	0	0.00		2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
326973	\N	Karolina	Kowal	4649	4342	2025-06-24 19:48:54.333136-05	nndz-WlNlOXdMMzdqQT09	4513	t	\N	1	2	33.30		2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
326974	\N	Hillary	Lupo	4649	4342	2025-06-24 19:48:54.333136-05	nndz-WlNlNnhyejZoZz09	4513	t	\N	0	0	0.00		2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
326975	\N	Alicia	Phillips	4649	4342	2025-06-24 19:48:54.333136-05	nndz-WlNlOXdMMzRoUT09	4513	t	\N	0	0	0.00		2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
326976	\N	Marion	Rice	4649	4342	2025-06-24 19:48:54.333136-05	nndz-WlNlOXdMLzlqUT09	4513	t	\N	0	0	0.00		2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
326977	\N	Dawn	Tepper	4649	4342	2025-06-24 19:48:54.333136-05	nndz-WkM2eHhyeitndz09	4513	t	\N	1	2	33.30		2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
326978	\N	Mary	Tracy	4649	4342	2025-06-24 19:48:54.333136-05	nndz-WkM2eHhyMy9ndz09	4513	t	\N	0	0	0.00		2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
326979	\N	Jennifer	Walsh	4649	4342	2025-06-24 19:48:54.333136-05	nndz-WlNhOXhMMzdnQT09	4513	t	\N	0	1	0.00		2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
326980	\N	Clyde	Woods	4642	4434	2025-06-24 19:48:54.333136-05	nndz-WkMrNnhMZjlnQT09	4514	t	\N	0	0	0.00	C	2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
326981	\N	Mark	Fessler	4642	4434	2025-06-24 19:48:54.333136-05	nndz-WkMrNnhMcjVqQT09	4514	t	\N	0	0	0.00	CC	2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
326982	\N	Rick	Aguayo	4642	4434	2025-06-24 19:48:54.333136-05	nndz-WkMrNnhMajRqQT09	4514	t	\N	0	0	0.00		2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
326983	\N	Mark	Ainsworth	4642	4434	2025-06-24 19:48:54.333136-05	nndz-WkMrNnhMMzdqQT09	4514	t	\N	0	0	0.00		2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
326984	\N	Carlos	Alcantar	4642	4434	2025-06-24 19:48:54.333136-05	nndz-WkMrOXlMMzRoQT09	4514	t	\N	1	0	100.00		2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
326985	\N	David	Altman	4642	4434	2025-06-24 19:48:54.333136-05	nndz-WkMrOHdyanhnUT09	4514	t	\N	0	0	0.00		2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
326986	\N	Michael	Bartello	4642	4434	2025-06-24 19:48:54.333136-05	nndz-WkMrNnhMZjVqUT09	4514	t	\N	0	0	0.00		2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
326987	\N	Chuck	Blumenthal	4642	4434	2025-06-24 19:48:54.333136-05	nndz-WkMrNng3LytnQT09	4514	t	\N	0	0	0.00		2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
326988	\N	Howard	Gartzman	4642	4434	2025-06-24 19:48:54.333136-05	nndz-WkMrOXlMdjVodz09	4514	t	\N	0	0	0.00		2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
326989	\N	Andrew	Ginsberg	4642	4434	2025-06-24 19:48:54.333136-05	nndz-WkMrNng3cjRoUT09	4514	t	\N	0	0	0.00		2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
326990	\N	Anthony	Goce	4642	4434	2025-06-24 19:48:54.333136-05	nndz-WkMrOHdiN3dqUT09	4514	t	\N	0	0	0.00		2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
326991	\N	Larry	Gold	4642	4434	2025-06-24 19:48:54.333136-05	nndz-WkMrNng3LytqQT09	4514	t	\N	0	0	0.00		2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
326992	\N	Conrad	Gordon	4642	4434	2025-06-24 19:48:54.333136-05	nndz-WkMrNng3L3hodz09	4514	t	\N	0	0	0.00		2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
326993	\N	Freddy	Hasnovi	4642	4434	2025-06-24 19:48:54.333136-05	nndz-WlNlNHdMNy9oUT09	4514	t	\N	0	0	0.00		2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
326994	\N	Paul	James	4642	4434	2025-06-24 19:48:54.333136-05	nndz-WkMrNnhMcjRnUT09	4514	t	\N	0	0	0.00		2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
326995	\N	Russ	Kerr	4642	4434	2025-06-24 19:48:54.333136-05	nndz-WkMrNng3LytnUT09	4514	t	\N	0	0	0.00		2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
326996	\N	Greg	Korak	4642	4434	2025-06-24 19:48:54.333136-05	nndz-WkMrNnhMMzlodz09	4514	t	\N	0	0	0.00		2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
326997	\N	Dragisa	Kupresak	4642	4434	2025-06-24 19:48:54.333136-05	nndz-WlNhd3lMdjdnQT09	4514	t	\N	0	0	0.00		2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
326998	\N	John	Lubner	4642	4434	2025-06-24 19:48:54.333136-05	nndz-WkMrOHdyajRoQT09	4514	t	\N	0	0	0.00		2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
326999	\N	Eric	Matten	4642	4434	2025-06-24 19:48:54.333136-05	nndz-WkMrNnhMai9qQT09	4514	t	\N	0	0	0.00		2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
327000	\N	Garvin	Murray	4642	4434	2025-06-24 19:48:54.333136-05	nndz-WlNlNXhybjlqUT09	4514	t	\N	0	0	0.00		2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
327001	\N	Jay	Navario	4642	4434	2025-06-24 19:48:54.333136-05	nndz-WkMrOHhyNzhodz09	4514	t	\N	0	0	0.00		2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
327002	\N	Russ	Needles	4642	4434	2025-06-24 19:48:54.333136-05	nndz-WkMrOXlMdjVnZz09	4514	t	\N	0	0	0.00		2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
327003	\N	Kenneth	Nini	4642	4434	2025-06-24 19:48:54.333136-05	nndz-WkMrOXlMcndoQT09	4514	t	\N	0	0	0.00		2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
327004	\N	Luiz	Pedrosa	4642	4434	2025-06-24 19:48:54.333136-05	nndz-WlNlNHhiejRndz09	4514	t	\N	0	0	0.00		2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
327005	\N	Steve	Ptasinski	4642	4434	2025-06-24 19:48:54.333136-05	nndz-WkMrNnhMcjVndz09	4514	t	\N	0	0	0.00		2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
327006	\N	Jonny	Rabb	4642	4434	2025-06-24 19:48:54.333136-05	nndz-WlNlNXhydjVnQT09	4514	t	\N	0	0	0.00		2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
327007	\N	Mark	Rawlins	4642	4434	2025-06-24 19:48:54.333136-05	nndz-WkMrOXlMdjVqUT09	4514	t	\N	0	0	0.00		2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
327008	\N	Brian	Toba	4642	4434	2025-06-24 19:48:54.333136-05	nndz-WkMrOHdieitoQT09	4514	t	\N	0	0	0.00		2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
327009	\N	Peter	Toth	4642	4434	2025-06-24 19:48:54.333136-05	nndz-WkMrOXlMcndodz09	4514	t	\N	0	0	0.00		2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
327010	\N	Dennis	Tysi	4642	4434	2025-06-24 19:48:54.333136-05	nndz-WkMrOHliMzVnQT09	4514	t	\N	0	0	0.00		2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
327011	\N	Caesar	Uribe	4642	4434	2025-06-24 19:48:54.333136-05	nndz-WkMrOXlMcndoZz09	4514	t	\N	0	0	0.00		2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
327012	\N	Joe	Zabat	4642	4434	2025-06-24 19:48:54.333136-05	nndz-WkMrOHc3LytnUT09	4514	t	\N	0	0	0.00		2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
327013	\N	Paul	Zuffa	4642	4434	2025-06-24 19:48:54.333136-05	nndz-WlNhd3lMMzZnUT09	4514	t	\N	0	0	0.00		2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
327014	\N	Tom	Handler	4646	4434	2025-06-24 19:48:54.333136-05	nndz-WkMrNnhMMzZnUT09	4514	t	\N	0	0	0.00	C	2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
327015	\N	Pat	Fragassi	4646	4434	2025-06-24 19:48:54.333136-05	nndz-WkMrOXliMy9nUT09	4514	t	\N	0	0	0.00	CC	2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
327016	\N	Steve	Albrecht	4646	4434	2025-06-24 19:48:54.333136-05	nndz-WkMrNnhMci9ndz09	4514	t	\N	0	1	0.00		2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
327017	\N	J	Balon	4646	4434	2025-06-24 19:48:54.333136-05	nndz-WlNhd3lMdjRndz09	4514	t	\N	0	0	0.00		2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
327018	\N	Tom	Berger	4646	4434	2025-06-24 19:48:54.333136-05	nndz-WkMrNnhMZjRnUT09	4514	t	\N	0	0	0.00		2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
327019	\N	Dan	Connolly	4646	4434	2025-06-24 19:48:54.333136-05	nndz-WkMrNnhMcjdnUT09	4514	t	\N	0	0	0.00		2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
327020	\N	Unknown	Friedman	4646	4434	2025-06-24 19:48:54.333136-05	nndz-WlNhd3lMdjdoUT09	4514	t	\N	0	0	0.00		2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
327021	\N	Andrew	Meyer	4646	4434	2025-06-24 19:48:54.333136-05	nndz-WlNlNXhybjlnZz09	4514	t	\N	0	0	0.00		2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
327022	\N	Eric	Orsic	4646	4434	2025-06-24 19:48:54.333136-05	nndz-WkMrNng3ejRoQT09	4514	t	\N	0	0	0.00		2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
327023	\N	Unknown	Sarkett	4646	4434	2025-06-24 19:48:54.333136-05	nndz-WlNlNXlMYndnUT09	4514	t	\N	0	0	0.00		2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
327024	\N	Scott	Ummel	4646	4434	2025-06-24 19:48:54.333136-05	nndz-WkMrNng3ejVnUT09	4514	t	\N	0	0	0.00		2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
327025	\N	Unknown	Ummel	4646	4434	2025-06-24 19:48:54.333136-05	nndz-WlNhd3lMdjRnZz09	4514	t	\N	0	0	0.00		2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
327026	\N	Unknown	Veddar	4646	4434	2025-06-24 19:48:54.333136-05	nndz-WlNhd3lMdjRqQT09	4514	t	\N	0	0	0.00		2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
327027	\N	unknown	Vedder	4646	4434	2025-06-24 19:48:54.333136-05	nndz-WlNlNXlMYndodz09	4514	t	\N	0	0	0.00		2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
327028	\N	Todd	Wagner	4646	4434	2025-06-24 19:48:54.333136-05	nndz-WlNhd3lMdjdoZz09	4514	t	\N	0	0	0.00		2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
327029	\N	Unknown	Wood	4646	4434	2025-06-24 19:48:54.333136-05	nndz-WlNlNXlMYndoUT09	4514	t	\N	0	0	0.00		2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
327030	\N	Bobby	Miller	4571	4430	2025-06-24 19:48:54.333136-05	nndz-WkMrNnhMajloZz09	4514	t	\N	0	0	0.00	C	2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
327031	\N	Birchwood	2	4571	4430	2025-06-24 19:48:54.333136-05	nndz-WlNlNXdibnhoQT09	4514	t	\N	0	0	0.00		2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
327032	\N	Howard	Abrams	4571	4430	2025-06-24 19:48:54.333136-05	nndz-WkMrNng3LzRndz09	4514	t	\N	0	0	0.00		2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
327033	\N	Alan	Abramson	4571	4430	2025-06-24 19:48:54.333136-05	nndz-WkMrNnhMbnhoZz09	4514	t	\N	0	0	0.00		2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
327034	\N	Jacob	Altman	4571	4430	2025-06-24 19:48:54.333136-05	nndz-WkMrNng3eitndz09	4514	t	\N	0	0	0.00		2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
327035	\N	Randy	Altman	4571	4430	2025-06-24 19:48:54.333136-05	nndz-WkMrNnhMai9nUT09	4514	t	\N	0	0	0.00		2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
327036	\N	Fedor	Baev	4571	4430	2025-06-24 19:48:54.333136-05	nndz-WkMrOHlMbjhoQT09	4514	t	\N	0	0	0.00		2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
327037	\N	Adam	Berman	4571	4430	2025-06-24 19:48:54.333136-05	nndz-WkMrNng3NzZqQT09	4514	t	\N	0	0	0.00		2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
327038	\N	Andrew	Block	4571	4430	2025-06-24 19:48:54.333136-05	nndz-WkMrNnhMZjRnQT09	4514	t	\N	0	0	0.00		2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
327039	\N	Ricky	Bortz	4571	4430	2025-06-24 19:48:54.333136-05	nndz-WkMrOHdManhndz09	4514	t	\N	0	0	0.00		2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
327040	\N	Ethan	Cantor	4571	4430	2025-06-24 19:48:54.333136-05	nndz-WkMrNng3NzloZz09	4514	t	\N	1	0	100.00		2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
327041	\N	Lowell	Cantor	4571	4430	2025-06-24 19:48:54.333136-05	nndz-WkMrOHdManhodz09	4514	t	\N	1	0	100.00		2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
327042	\N	Engleman	Chris	4571	4430	2025-06-24 19:48:54.333136-05	nndz-WkMrNnhMbjVqUT09	4514	t	\N	1	0	100.00		2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
327043	\N	Jarrod	Cohen	4571	4430	2025-06-24 19:48:54.333136-05	nndz-WlNTNXhMejRodz09	4514	t	\N	0	1	0.00		2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
327044	\N	scott	Erinberg	4571	4430	2025-06-24 19:48:54.333136-05	nndz-WkMrNng3cjdoZz09	4514	t	\N	0	0	0.00		2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
327045	\N	Gregg	Falberg	4571	4430	2025-06-24 19:48:54.333136-05	nndz-WkMrNnhMajdndz09	4514	t	\N	0	0	0.00		2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
327046	\N	Jeff	Feldman	4571	4430	2025-06-24 19:48:54.333136-05	nndz-WkMrNng3LzRodz09	4514	t	\N	0	0	0.00		2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
327047	\N	George	Fenton	4571	4430	2025-06-24 19:48:54.333136-05	nndz-WkMrNnhMai9nZz09	4514	t	\N	2	0	100.00		2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
327048	\N	Robert	Fenton	4571	4430	2025-06-24 19:48:54.333136-05	nndz-WkMrNng3MzRqQT09	4514	t	\N	2	0	100.00		2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
327049	\N	Brandon	Fisher	4571	4430	2025-06-24 19:48:54.333136-05	nndz-WkMrOHdManhqUT09	4514	t	\N	0	0	0.00		2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
327050	\N	Steve	Fisher	4571	4430	2025-06-24 19:48:54.333136-05	nndz-WkMrNng3LzVnUT09	4514	t	\N	0	0	0.00		2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
327051	\N	Zach	Freed	4571	4430	2025-06-24 19:48:54.333136-05	nndz-WkMrNng3NzVoUT09	4514	t	\N	0	0	0.00		2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
327052	\N	Adam	Gooze	4571	4430	2025-06-24 19:48:54.333136-05	nndz-WkMrNng3LzlqQT09	4514	t	\N	1	0	100.00		2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
327053	\N	Marv	Gurevich	4571	4430	2025-06-24 19:48:54.333136-05	nndz-WkMrNng3NytnUT09	4514	t	\N	0	0	0.00		2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
327054	\N	Cory	Isaacson	4571	4430	2025-06-24 19:48:54.333136-05	nndz-WkMrNng3MzhnZz09	4514	t	\N	0	0	0.00		2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
327055	\N	Barry	Jacobs	4571	4430	2025-06-24 19:48:54.333136-05	nndz-WkMrNnhMdjlnQT09	4514	t	\N	0	0	0.00		2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
327056	\N	Howard	Klieger	4571	4430	2025-06-24 19:48:54.333136-05	nndz-WkMrNnhMai9oZz09	4514	t	\N	0	0	0.00		2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
327057	\N	Gabe	Korach	4571	4430	2025-06-24 19:48:54.333136-05	nndz-WkMrNnhMZi9nZz09	4514	t	\N	0	0	0.00		2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
327058	\N	Michael	Kosner	4571	4430	2025-06-24 19:48:54.333136-05	nndz-WkMrNnhMYjZoQT09	4514	t	\N	0	0	0.00		2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
327059	\N	Gregg	Levin	4571	4430	2025-06-24 19:48:54.333136-05	nndz-WkMrNng3ejZnUT09	4514	t	\N	0	0	0.00		2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
327060	\N	Vince	LoGrande	4571	4430	2025-06-24 19:48:54.333136-05	nndz-WkMrNnhMdjZoZz09	4514	t	\N	0	0	0.00		2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
327061	\N	David	Luger	4571	4430	2025-06-24 19:48:54.333136-05	nndz-WkMrNng3cjRndz09	4514	t	\N	0	0	0.00		2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
327062	\N	Michael	Mazursky	4571	4430	2025-06-24 19:48:54.333136-05	nndz-WkMrNnhMbjlqQT09	4514	t	\N	0	0	0.00		2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
327063	\N	Ari	Mintzer	4571	4430	2025-06-24 19:48:54.333136-05	nndz-WkMrNng3LzVqUT09	4514	t	\N	0	0	0.00		2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
327064	\N	Adam	Morgan	4571	4430	2025-06-24 19:48:54.333136-05	nndz-WkMrNng3Nytndz09	4514	t	\N	1	0	100.00		2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
327065	\N	Bruce	Pinsof	4571	4430	2025-06-24 19:48:54.333136-05	nndz-WkMrNnhMajloQT09	4514	t	\N	0	1	0.00		2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
327066	\N	Jon	Primer	4571	4430	2025-06-24 19:48:54.333136-05	nndz-WkMrNnhMYjZodz09	4514	t	\N	0	0	0.00		2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
327067	\N	Dave	Raab	4571	4430	2025-06-24 19:48:54.333136-05	nndz-WkMrNng3LzlqUT09	4514	t	\N	0	0	0.00		2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
327068	\N	Jonny	Raab	4571	4430	2025-06-24 19:48:54.333136-05	nndz-WkMrOHlMbjhodz09	4514	t	\N	0	0	0.00		2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
327069	\N	Steve	Rotblatt	4571	4430	2025-06-24 19:48:54.333136-05	nndz-WkMrNnhMbjRqUT09	4514	t	\N	1	1	50.00		2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
327070	\N	Steve	Rudman	4571	4430	2025-06-24 19:48:54.333136-05	nndz-WkMrNng3LzhoZz09	4514	t	\N	0	0	0.00		2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
327071	\N	Gabe	Schlussel	4571	4430	2025-06-24 19:48:54.333136-05	nndz-WkMrNng3NzdnZz09	4514	t	\N	2	0	100.00		2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
327072	\N	Jonah	Shapiro	4571	4430	2025-06-24 19:48:54.333136-05	nndz-WlNTNXhMejRnUT09	4514	t	\N	1	0	100.00		2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
327073	\N	Stuart	Shiner	4571	4430	2025-06-24 19:48:54.333136-05	nndz-WkMrOHdManhqQT09	4514	t	\N	0	0	0.00		2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
327074	\N	Larry	Tarshis	4571	4430	2025-06-24 19:48:54.333136-05	nndz-WkMrNng3Lzlndz09	4514	t	\N	0	0	0.00		2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
327075	\N	Bob	Wise	4571	4430	2025-06-24 19:48:54.333136-05	nndz-WkMrNng3Ly9oQT09	4514	t	\N	1	0	100.00		2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
327076	\N	Darren	Zeidel	4571	4430	2025-06-24 19:48:54.333136-05	nndz-WkMrNng3M3doUT09	4514	t	\N	0	0	0.00		2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
327077	\N	Mike	Zucker	4571	4430	2025-06-24 19:48:54.333136-05	nndz-WkMrNng3LzhnUT09	4514	t	\N	0	0	0.00		2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
327078	\N	Tony	Fiordaliso	4600	4430	2025-06-24 19:48:54.333136-05	nndz-WkMrNnhMditqUT09	4514	t	\N	0	0	0.00	C	2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
327079	\N	Gui	Axus	4600	4430	2025-06-24 19:48:54.333136-05	nndz-WkMrNng3MzZnQT09	4514	t	\N	0	1	0.00		2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
327080	\N	Bob	Biddle	4600	4430	2025-06-24 19:48:54.333136-05	nndz-WkMrNnhMditodz09	4514	t	\N	0	1	0.00		2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
327081	\N	Stephen	Cervieri	4600	4430	2025-06-24 19:48:54.333136-05	nndz-WkMrOXlMbjlndz09	4514	t	\N	0	0	0.00		2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
327082	\N	David	Hunt	4600	4430	2025-06-24 19:48:54.333136-05	nndz-WkMrNng3LzZoZz09	4514	t	\N	1	0	100.00		2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
327083	\N	Doug	Lee	4600	4430	2025-06-24 19:48:54.333136-05	nndz-WkMrNng3LzdqQT09	4514	t	\N	0	1	0.00		2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
327084	\N	Chris	Longeway	4600	4430	2025-06-24 19:48:54.333136-05	nndz-WkMrOHdMLzlnZz09	4514	t	\N	0	1	0.00		2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
327085	\N	Mike	McCullough	4600	4430	2025-06-24 19:48:54.333136-05	nndz-WkMrNng3MzZnUT09	4514	t	\N	0	1	0.00		2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
327086	\N	Ken	Mick	4600	4430	2025-06-24 19:48:54.333136-05	nndz-WkMrNnhMajZoZz09	4514	t	\N	0	0	0.00		2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
327087	\N	Tim	Richmond	4600	4430	2025-06-24 19:48:54.333136-05	nndz-WkMrNng3Mytndz09	4514	t	\N	0	1	0.00		2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
327088	\N	Mark	Schacher	4600	4430	2025-06-24 19:48:54.333136-05	nndz-WkMrNnhMajdnUT09	4514	t	\N	0	1	0.00		2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
327089	\N	Jack	Schwab	4600	4430	2025-06-24 19:48:54.333136-05	nndz-WlNld3hyNzhodz09	4514	t	\N	0	1	0.00		2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
327090	\N	Paul	Sundberg	4600	4430	2025-06-24 19:48:54.333136-05	nndz-WkMrNnhMYjVoQT09	4514	t	\N	1	0	100.00		2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
327091	\N	Mark	Trager	4600	4430	2025-06-24 19:48:54.333136-05	nndz-WkMrNnhMdjVnUT09	4514	t	\N	0	1	0.00		2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
327092	\N	Rob	Busam	4600	4430	2025-06-24 19:48:54.333136-05	nndz-WkMrNng3NzRodz09	4514	t	\N	1	1	50.00		2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
327093	\N	Steve	Carver	4600	4430	2025-06-24 19:48:54.333136-05	nndz-WkMrNng3cjRoQT09	4514	t	\N	0	0	0.00		2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
327094	\N	Hunter	Gordy	4600	4430	2025-06-24 19:48:54.333136-05	nndz-WkMrNng3LzZoQT09	4514	t	\N	1	0	100.00		2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
327095	\N	Will	Lindquist	4600	4430	2025-06-24 19:48:54.333136-05	nndz-WkMrOXlMbjlnZz09	4514	t	\N	0	1	0.00		2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
327096	\N	Ted	North	4600	4430	2025-06-24 19:48:54.333136-05	nndz-WkMrNng3MzZnZz09	4514	t	\N	0	0	0.00		2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
327097	\N	Andy	Pfahl	4600	4430	2025-06-24 19:48:54.333136-05	nndz-WkMrOXlMbjlqQT09	4514	t	\N	1	0	100.00		2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
327098	\N	scott	smith	4610	4430	2025-06-24 19:48:54.333136-05	nndz-WkMrNnhMdjZqUT09	4514	t	\N	0	0	0.00	C	2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
327099	\N	Matt	Alvis	4610	4430	2025-06-24 19:48:54.333136-05	nndz-WlNlNXlMcndoQT09	4514	t	\N	0	0	0.00		2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
327100	\N	Howard	Braun	4610	4430	2025-06-24 19:48:54.333136-05	nndz-WkMrNng3LzZnQT09	4514	t	\N	0	0	0.00		2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
327101	\N	Cliff	Breslow	4610	4430	2025-06-24 19:48:54.333136-05	nndz-WkMrNnhMYnhnQT09	4514	t	\N	0	0	0.00		2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
327102	\N	Rob	Cal	4610	4430	2025-06-24 19:48:54.333136-05	nndz-WkMrNnhMbjdoUT09	4514	t	\N	0	0	0.00		2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
327103	\N	Jon	Cooper	4610	4430	2025-06-24 19:48:54.333136-05	nndz-WkMrOXliZjdqUT09	4514	t	\N	0	0	0.00		2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
327104	\N	Felix	Danciu	4610	4430	2025-06-24 19:48:54.333136-05	nndz-WkMrNng3endqUT09	4514	t	\N	0	0	0.00		2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
327105	\N	Dmitry	Edelchik	4610	4430	2025-06-24 19:48:54.333136-05	nndz-WkMrNng3MzZqQT09	4514	t	\N	0	0	0.00		2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
327106	\N	Steve	Ewaldz	4610	4430	2025-06-24 19:48:54.333136-05	nndz-WkMrNnhMMzloQT09	4514	t	\N	0	1	0.00		2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
327107	\N	Brett	Fenton	4610	4430	2025-06-24 19:48:54.333136-05	nndz-WkMrNnhMajZndz09	4514	t	\N	0	0	0.00		2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
327108	\N	Rich	Foss	4610	4430	2025-06-24 19:48:54.333136-05	nndz-WkMrOXliZjdnZz09	4514	t	\N	1	0	100.00		2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
327109	\N	Jay	Freedman	4610	4430	2025-06-24 19:48:54.333136-05	nndz-WkMrNnhMajVndz09	4514	t	\N	0	0	0.00		2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
327110	\N	Michael	Freund	4610	4430	2025-06-24 19:48:54.333136-05	nndz-WkMrOXliZjRnUT09	4514	t	\N	0	0	0.00		2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
327111	\N	Mike	Haber	4610	4430	2025-06-24 19:48:54.333136-05	nndz-WlNlNXlMcndnQT09	4514	t	\N	0	0	0.00		2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
327112	\N	Jacek	Jacek	4610	4430	2025-06-24 19:48:54.333136-05	nndz-WlNlNXlMcndnZz09	4514	t	\N	0	0	0.00		2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
327113	\N	Andy	Jonak	4610	4430	2025-06-24 19:48:54.333136-05	nndz-WlNlNXlMcndnUT09	4514	t	\N	0	0	0.00		2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
327114	\N	Mark	Juhl	4610	4430	2025-06-24 19:48:54.333136-05	nndz-WkMrNng3NzhqUT09	4514	t	\N	0	0	0.00		2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
327115	\N	Jimmy	Klein	4610	4430	2025-06-24 19:48:54.333136-05	nndz-WkMrOXliZjRqUT09	4514	t	\N	0	0	0.00		2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
327116	\N	Jae	Lee	4610	4430	2025-06-24 19:48:54.333136-05	nndz-WkMrNng3endqQT09	4514	t	\N	0	0	0.00		2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
327117	\N	Brian	Levitas	4610	4430	2025-06-24 19:48:54.333136-05	nndz-WlNhd3hMbjdndz09	4514	t	\N	0	0	0.00		2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
327118	\N	Joe	Lyden	4610	4430	2025-06-24 19:48:54.333136-05	nndz-WkMrOXliZjRodz09	4514	t	\N	0	0	0.00		2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
327119	\N	Derek	Majka	4610	4430	2025-06-24 19:48:54.333136-05	nndz-WkMrNng3MzhqQT09	4514	t	\N	0	0	0.00		2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
327120	\N	Steve	Mesirow	4610	4430	2025-06-24 19:48:54.333136-05	nndz-WkMrNng3MzVoUT09	4514	t	\N	0	0	0.00		2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
327121	\N	Geoff	Miller	4610	4430	2025-06-24 19:48:54.333136-05	nndz-WkMrNng3Ny9nQT09	4514	t	\N	0	0	0.00		2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
327122	\N	Alax	Paz	4610	4430	2025-06-24 19:48:54.333136-05	nndz-WkMrNng3MzRoUT09	4514	t	\N	0	0	0.00		2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
327123	\N	Alex	Paz	4610	4430	2025-06-24 19:48:54.333136-05	nndz-WkMrOXliZjRnQT09	4514	t	\N	0	0	0.00		2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
327124	\N	Richard	Sarhaddi	4610	4430	2025-06-24 19:48:54.333136-05	nndz-WlNhd3hyYjdqUT09	4514	t	\N	0	0	0.00		2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
327125	\N	Tom	Stotter	4610	4430	2025-06-24 19:48:54.333136-05	nndz-WkMrNng3cjlnQT09	4514	t	\N	0	0	0.00		2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
327126	\N	Aaron	Walsh	4610	4430	2025-06-24 19:48:54.333136-05	nndz-WkMrNng3cjRnUT09	4514	t	\N	0	0	0.00		2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
327127	\N	Justin	Wellen	4610	4430	2025-06-24 19:48:54.333136-05	nndz-WkMrOXlMajVqUT09	4514	t	\N	0	0	0.00		2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
327128	\N	zdzislaw	zieba	4610	4430	2025-06-24 19:48:54.333136-05	nndz-WkMrNng3cjlqUT09	4514	t	\N	0	0	0.00		2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
327129	\N	Prezemk	Zielinski	4610	4430	2025-06-24 19:48:54.333136-05	nndz-WlNlNXlMcndndz09	4514	t	\N	0	0	0.00		2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
327130	\N	Dave	Travetto	4638	4430	2025-06-24 19:48:54.333136-05	nndz-WkMrNnhMMy9nQT09	4514	t	\N	0	0	0.00	C	2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
327131	\N	Curtis	Baddeley	4638	4430	2025-06-24 19:48:54.333136-05	nndz-WkMrNng3ejRodz09	4514	t	\N	0	1	0.00		2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
327132	\N	Mark	Burnosky	4638	4430	2025-06-24 19:48:54.333136-05	nndz-WkMrOHc3ZnhnQT09	4514	t	\N	0	0	0.00		2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
327133	\N	Bryan	Caruso	4638	4430	2025-06-24 19:48:54.333136-05	nndz-WkMrNnhMZndodz09	4514	t	\N	0	0	0.00		2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
327134	\N	Phil	Davis	4638	4430	2025-06-24 19:48:54.333136-05	nndz-WkMrNnhMdjdnQT09	4514	t	\N	0	0	0.00		2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
327135	\N	Jim	Franke	4638	4430	2025-06-24 19:48:54.333136-05	nndz-WkMrNnhMcjhodz09	4514	t	\N	0	0	0.00		2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
327136	\N	Steve	Fretzin	4638	4430	2025-06-24 19:48:54.333136-05	nndz-WkMrNng3ejhqQT09	4514	t	\N	0	0	0.00		2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
327137	\N	Billy	Friedman	4638	4430	2025-06-24 19:48:54.333136-05	nndz-WlNld3libitqUT09	4514	t	\N	1	0	100.00		2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
327138	\N	Ed	Granger	4638	4430	2025-06-24 19:48:54.333136-05	nndz-WkMrNnhMajVoQT09	4514	t	\N	0	1	0.00		2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
327139	\N	Mitch	Granger	4638	4430	2025-06-24 19:48:54.333136-05	nndz-WkMrOHdibjdoQT09	4514	t	\N	0	0	0.00		2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
327140	\N	Joshua	Gray	4638	4430	2025-06-24 19:48:54.333136-05	nndz-WlNld3lMajloZz09	4514	t	\N	0	1	0.00		2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
327141	\N	Brian	Hanover	4638	4430	2025-06-24 19:48:54.333136-05	nndz-WkMrNng3ejhoZz09	4514	t	\N	0	0	0.00		2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
327142	\N	Brian	Hardner	4638	4430	2025-06-24 19:48:54.333136-05	nndz-WkMrOHc3ZnhoZz09	4514	t	\N	0	1	0.00		2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
327143	\N	Chris	Kosky	4638	4430	2025-06-24 19:48:54.333136-05	nndz-WkMrNnhMcndnZz09	4514	t	\N	0	1	0.00		2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
327144	\N	Kevin	LaPiana	4638	4430	2025-06-24 19:48:54.333136-05	nndz-WlNlNHhMejRnQT09	4514	t	\N	0	0	0.00		2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
327145	\N	Pat	Marschall	4638	4430	2025-06-24 19:48:54.333136-05	nndz-WkMrNnhMYitoZz09	4514	t	\N	0	1	0.00		2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
327146	\N	Jeff	Moran	4638	4430	2025-06-24 19:48:54.333136-05	nndz-WkMrNng3MzhoZz09	4514	t	\N	0	0	0.00		2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
327147	\N	Don	O'Malley	4638	4430	2025-06-24 19:48:54.333136-05	nndz-WlNlNXliandoZz09	4514	t	\N	0	0	0.00		2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
327148	\N	Paul	P. Patt	4638	4430	2025-06-24 19:48:54.333136-05	nndz-WkMrOHhiLzZnQT09	4514	t	\N	0	0	0.00		2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
327149	\N	Brett	Pierson	4638	4430	2025-06-24 19:48:54.333136-05	nndz-WlNlNXhyMzRoQT09	4514	t	\N	0	0	0.00		2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
327150	\N	James	Redland	4638	4430	2025-06-24 19:48:54.333136-05	nndz-WkMrNng3ei9oZz09	4514	t	\N	0	0	0.00		2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
327151	\N	Kevin	P. Ryan	4638	4430	2025-06-24 19:48:54.333136-05	nndz-WkMrOHc3ZnhnZz09	4514	t	\N	0	0	0.00		2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
327152	\N	Noah	S. Ryan	4638	4430	2025-06-24 19:48:54.333136-05	nndz-WkMrOHc3ZnhqUT09	4514	t	\N	0	0	0.00		2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
327153	\N	Sid	Siegel	4638	4430	2025-06-24 19:48:54.333136-05	nndz-WkMrNnhMdjRoZz09	4514	t	\N	0	0	0.00		2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
327154	\N	Michael	Sims	4638	4430	2025-06-24 19:48:54.333136-05	nndz-WkMrNnhMandqQT09	4514	t	\N	1	0	100.00		2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
327155	\N	Marty	Singer	4638	4430	2025-06-24 19:48:54.333136-05	nndz-WlNld3libitnZz09	4514	t	\N	0	1	0.00		2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
327156	\N	Justin	Stahl	4638	4430	2025-06-24 19:48:54.333136-05	nndz-WkMrNng3MzlnQT09	4514	t	\N	0	0	0.00		2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
327157	\N	Adam	Weiss	4638	4430	2025-06-24 19:48:54.333136-05	nndz-WkMrNnhMajhqQT09	4514	t	\N	0	0	0.00		2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
327158	\N	JoJo	Yap	4638	4430	2025-06-24 19:48:54.333136-05	nndz-WkMrNnhManhoUT09	4514	t	\N	0	1	0.00		2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
327159	\N	Clyde	Woods	4642	4430	2025-06-24 19:48:54.333136-05	nndz-WkMrNnhMZjlnQT09	4514	t	\N	0	0	0.00	C	2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
327160	\N	Rick	Aguayo	4642	4430	2025-06-24 19:48:54.333136-05	nndz-WkMrNnhMajRqQT09	4514	t	\N	0	0	0.00	CC	2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
327161	\N	Mark	Ainsworth	4642	4430	2025-06-24 19:48:54.333136-05	nndz-WkMrNnhMMzdqQT09	4514	t	\N	0	0	0.00		2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
327162	\N	Carlos	Alcantar	4642	4430	2025-06-24 19:48:54.333136-05	nndz-WkMrOXlMMzRoQT09	4514	t	\N	1	0	100.00		2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
327163	\N	James	Balon	4642	4430	2025-06-24 19:48:54.333136-05	nndz-WlNlNXhyai9ndz09	4514	t	\N	0	1	0.00		2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
327164	\N	Chuck	Blumenthal	4642	4430	2025-06-24 19:48:54.333136-05	nndz-WkMrNng3LytnQT09	4514	t	\N	0	0	0.00		2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
327165	\N	Brian	Bonds	4642	4430	2025-06-24 19:48:54.333136-05	nndz-WlNld3liZjRnZz09	4514	t	\N	0	0	0.00		2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
327166	\N	Tom	Conradi	4642	4430	2025-06-24 19:48:54.333136-05	nndz-WkMrNng3ejRqUT09	4514	t	\N	0	0	0.00		2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
327167	\N	Rex	Daarol	4642	4430	2025-06-24 19:48:54.333136-05	nndz-WlNhd3liejdodz09	4514	t	\N	0	1	0.00		2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
327168	\N	Adam	Davis	4642	4430	2025-06-24 19:48:54.333136-05	nndz-WlNhd3lMM3dndz09	4514	t	\N	0	0	0.00		2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
327169	\N	Ernesto	Diaz	4642	4430	2025-06-24 19:48:54.333136-05	nndz-WlNlNXhyMzVnUT09	4514	t	\N	0	0	0.00		2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
327170	\N	Mark	Fessler	4642	4430	2025-06-24 19:48:54.333136-05	nndz-WkMrNnhMcjVqQT09	4514	t	\N	0	0	0.00		2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
327171	\N	Ceasar	Fuenticilla	4642	4430	2025-06-24 19:48:54.333136-05	nndz-WkMrOHdiYjRoUT09	4514	t	\N	1	0	100.00		2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
327172	\N	Terrence	Gamboa	4642	4430	2025-06-24 19:48:54.333136-05	nndz-WlNTNXhMNzhnZz09	4514	t	\N	0	0	0.00		2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
327173	\N	Howard	Gartzman	4642	4430	2025-06-24 19:48:54.333136-05	nndz-WlNhd3liNzVoQT09	4514	t	\N	0	0	0.00		2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
327174	\N	Eric	Gordon	4642	4430	2025-06-24 19:48:54.333136-05	nndz-WlNlNHdMNytodz09	4514	t	\N	0	0	0.00		2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
327175	\N	Ben	Grais	4642	4430	2025-06-24 19:48:54.333136-05	nndz-WkMrNng3M3dqUT09	4514	t	\N	0	0	0.00		2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
327176	\N	Mark	Hanson	4642	4430	2025-06-24 19:48:54.333136-05	nndz-WlNld3liZjRqUT09	4514	t	\N	0	1	0.00		2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
327177	\N	Freddy	Hasnovi	4642	4430	2025-06-24 19:48:54.333136-05	nndz-WlNlNHdMNytoQT09	4514	t	\N	0	0	0.00		2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
327178	\N	Paul	James	4642	4430	2025-06-24 19:48:54.333136-05	nndz-WkMrNnhMcjRnUT09	4514	t	\N	0	0	0.00		2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
327179	\N	Russ	Kerr	4642	4430	2025-06-24 19:48:54.333136-05	nndz-WlNhd3liNzVodz09	4514	t	\N	0	1	0.00		2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
327180	\N	Greg	Korak	4642	4430	2025-06-24 19:48:54.333136-05	nndz-WkMrNnhMMzlodz09	4514	t	\N	0	0	0.00		2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
327181	\N	Rex	Lao	4642	4430	2025-06-24 19:48:54.333136-05	nndz-WkMrOHdibi9qQT09	4514	t	\N	0	1	0.00		2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
327182	\N	Dan	Lek	4642	4430	2025-06-24 19:48:54.333136-05	nndz-WlNhd3lMMzZnQT09	4514	t	\N	0	0	0.00		2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
327183	\N	John	Leubner	4642	4430	2025-06-24 19:48:54.333136-05	nndz-WkMrNng3cjloZz09	4514	t	\N	0	0	0.00		2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
327184	\N	Eric	Matten	4642	4430	2025-06-24 19:48:54.333136-05	nndz-WkMrNnhMai9qQT09	4514	t	\N	0	0	0.00		2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
327185	\N	Garvin	Murray	4642	4430	2025-06-24 19:48:54.333136-05	nndz-WlNlNXg3ZjZqUT09	4514	t	\N	0	0	0.00		2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
327186	\N	John	Mysz	4642	4430	2025-06-24 19:48:54.333136-05	nndz-WlNlNXdML3hodz09	4514	t	\N	0	0	0.00		2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
327187	\N	Jay	Nazario	4642	4430	2025-06-24 19:48:54.333136-05	nndz-WkMrOHdyZnhoQT09	4514	t	\N	0	0	0.00		2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
327188	\N	Juan	Pagador	4642	4430	2025-06-24 19:48:54.333136-05	nndz-WkMrOHdiYjRodz09	4514	t	\N	0	0	0.00		2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
327189	\N	Steve	Ptasinski	4642	4430	2025-06-24 19:48:54.333136-05	nndz-WkMrNnhMcjVndz09	4514	t	\N	0	0	0.00		2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
327190	\N	John	Rabb	4642	4430	2025-06-24 19:48:54.333136-05	nndz-WlNlNXg3bjlnZz09	4514	t	\N	0	0	0.00		2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
327191	\N	Jonny	Rabb	4642	4430	2025-06-24 19:48:54.333136-05	nndz-WlNlNXhyai9nZz09	4514	t	\N	0	0	0.00		2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
327192	\N	Tom	Rebarchak	4642	4430	2025-06-24 19:48:54.333136-05	nndz-WkMrNnhMMzloZz09	4514	t	\N	0	0	0.00		2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
327193	\N	Andy	Snyder	4642	4430	2025-06-24 19:48:54.333136-05	nndz-WlNld3liZjRndz09	4514	t	\N	0	1	0.00		2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
327194	\N	Dan	Stolar	4642	4430	2025-06-24 19:48:54.333136-05	nndz-WkMrOHdibjdodz09	4514	t	\N	0	0	0.00		2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
327195	\N	Scott	Ummel	4642	4430	2025-06-24 19:48:54.333136-05	nndz-WlNlNXg3ZjZqQT09	4514	t	\N	0	0	0.00		2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
327196	\N	Cesar	Uribe	4642	4430	2025-06-24 19:48:54.333136-05	nndz-WkMrNnhMcjloUT09	4514	t	\N	0	0	0.00		2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
327197	\N	Todd	Wagner	4642	4430	2025-06-24 19:48:54.333136-05	nndz-WlNhd3lMdjdnZz09	4514	t	\N	0	0	0.00		2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
327198	\N	Todd	Wagner	4642	4430	2025-06-24 19:48:54.333136-05	nndz-WkMrNnhMdnhnUT09	4514	t	\N	0	0	0.00		2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
327199	\N	Brian	Welch	4642	4430	2025-06-24 19:48:54.333136-05	nndz-WlNhd3libjdndz09	4514	t	\N	0	0	0.00		2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
327200	\N	Eric	Yu	4642	4430	2025-06-24 19:48:54.333136-05	nndz-WkMrNnhMZitnQT09	4514	t	\N	0	0	0.00		2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
327201	\N	Joseph	Zabat	4642	4430	2025-06-24 19:48:54.333136-05	nndz-WkMrNnhMcjRoZz09	4514	t	\N	0	0	0.00		2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
327202	\N	Paul	Zuffa	4642	4430	2025-06-24 19:48:54.333136-05	nndz-WlNhd3libjdnQT09	4514	t	\N	0	0	0.00		2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
327203	\N	Paul	Zuffa	4642	4430	2025-06-24 19:48:54.333136-05	nndz-WlNhd3lMMzZoZz09	4514	t	\N	0	0	0.00		2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
327204	\N	Chas	Schinzer	4642	4430	2025-06-24 19:48:54.333136-05	nndz-WkMrNnhMbjdqQT09	4514	t	\N	1	0	100.00	C	2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
327205	\N	Marc	Adams	4642	4430	2025-06-24 19:48:54.333136-05	nndz-WkMrNng3LzloUT09	4514	t	\N	1	0	100.00		2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
327206	\N	Trace	Bower	4642	4430	2025-06-24 19:48:54.333136-05	nndz-WkMrNng3ejVoUT09	4514	t	\N	0	0	0.00		2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
327207	\N	John	Calkins	4642	4430	2025-06-24 19:48:54.333136-05	nndz-WkMrOHhiMzhoUT09	4514	t	\N	0	0	0.00		2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
327208	\N	Werner	Camoras	4642	4430	2025-06-24 19:48:54.333136-05	nndz-WkMrNnhMbjdnZz09	4514	t	\N	2	0	100.00		2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
327209	\N	Don	Chae	4642	4430	2025-06-24 19:48:54.333136-05	nndz-WkMrNnhMYjhnUT09	4514	t	\N	1	0	100.00		2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
327210	\N	Duan	Chen	4642	4430	2025-06-24 19:48:54.333136-05	nndz-WkMrNnhMYjRnQT09	4514	t	\N	2	0	100.00		2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
327211	\N	Todd	Dahlquist	4642	4430	2025-06-24 19:48:54.333136-05	nndz-WlNTNXhiLy9ndz09	4514	t	\N	1	0	100.00		2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
327212	\N	Dan	Desio	4642	4430	2025-06-24 19:48:54.333136-05	nndz-WkMrOHc3LzloZz09	4514	t	\N	0	1	0.00		2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
327213	\N	Bryan	Fernley	4642	4430	2025-06-24 19:48:54.333136-05	nndz-WlNhd3hyYjhnUT09	4514	t	\N	1	0	100.00		2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
327214	\N	carlos	flores	4642	4430	2025-06-24 19:48:54.333136-05	nndz-WlNlNHdyNzZndz09	4514	t	\N	0	0	0.00		2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
327215	\N	David	Hwang	4642	4430	2025-06-24 19:48:54.333136-05	nndz-WkMrNng3ejdnZz09	4514	t	\N	0	0	0.00		2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
327216	\N	Brenden	Lehr	4642	4430	2025-06-24 19:48:54.333136-05	nndz-WkMrOHc3LzlnUT09	4514	t	\N	0	0	0.00		2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
327217	\N	Youngbin	Lim	4642	4430	2025-06-24 19:48:54.333136-05	nndz-WlNTNXhiLy9nQT09	4514	t	\N	1	0	100.00		2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
327218	\N	John	Liu	4642	4430	2025-06-24 19:48:54.333136-05	nndz-WkMrNnhMZjZqUT09	4514	t	\N	0	0	0.00		2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
327219	\N	Rafa	Lozado	4642	4430	2025-06-24 19:48:54.333136-05	nndz-WlNlNXdienhnZz09	4514	t	\N	1	0	100.00		2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
327220	\N	Barry	Marks	4642	4430	2025-06-24 19:48:54.333136-05	nndz-WkMrOHhiMzhoQT09	4514	t	\N	0	0	0.00		2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
327221	\N	Al	Momongon	4642	4430	2025-06-24 19:48:54.333136-05	nndz-WkMrOHc3LzlnZz09	4514	t	\N	0	0	0.00		2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
327222	\N	David	More	4642	4430	2025-06-24 19:48:54.333136-05	nndz-WkMrNnhMMzZoUT09	4514	t	\N	0	0	0.00		2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
327223	\N	Luiz	Pedrosa	4642	4430	2025-06-24 19:48:54.333136-05	nndz-WlNhd3hyYjhndz09	4514	t	\N	0	1	0.00		2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
327224	\N	Alan	Polansky	4642	4430	2025-06-24 19:48:54.333136-05	nndz-WkMrOHhiMzhodz09	4514	t	\N	0	0	0.00		2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
327225	\N	Edgar	Raya	4642	4430	2025-06-24 19:48:54.333136-05	nndz-WkMrOHc3LzlnQT09	4514	t	\N	0	0	0.00		2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
327226	\N	Dave	Sargent	4642	4430	2025-06-24 19:48:54.333136-05	nndz-WlNhd3lMMzZoUT09	4514	t	\N	0	0	0.00		2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
327227	\N	Manish	Shah	4642	4430	2025-06-24 19:48:54.333136-05	nndz-WkMrNnhMbjZqQT09	4514	t	\N	1	0	100.00		2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
327228	\N	David	Shin	4642	4430	2025-06-24 19:48:54.333136-05	nndz-WlNhd3hyYjhnZz09	4514	t	\N	0	0	0.00		2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
327229	\N	Ken	Sitar	4642	4430	2025-06-24 19:48:54.333136-05	nndz-WkMrOHhiMzlqUT09	4514	t	\N	1	0	100.00		2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
327230	\N	Joe	Slaby	4642	4430	2025-06-24 19:48:54.333136-05	nndz-WkMrNnhMdjhqQT09	4514	t	\N	1	0	100.00		2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
327231	\N	Alfred	Tam	4642	4430	2025-06-24 19:48:54.333136-05	nndz-WkMrNng3MzloZz09	4514	t	\N	0	0	0.00		2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
327232	\N	Rodrigo	Angel	4580	4431	2025-06-24 19:48:54.333136-05	nndz-WkMrNng3M3hoQT09	4514	t	\N	1	0	100.00	C	2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
327233	\N	David	Barrett	4580	4431	2025-06-24 19:48:54.333136-05	nndz-WkMrOXlMMzdoQT09	4514	t	\N	0	0	0.00		2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
327234	\N	Jim	Bennett	4580	4431	2025-06-24 19:48:54.333136-05	nndz-WkMrOXlMMzZoQT09	4514	t	\N	0	0	0.00		2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
327235	\N	Doug	Bouton	4580	4431	2025-06-24 19:48:54.333136-05	nndz-WkMrOXlMMzdnUT09	4514	t	\N	0	0	0.00		2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
327236	\N	Ken	Brown	4580	4431	2025-06-24 19:48:54.333136-05	nndz-WkMrOXlMMzloUT09	4514	t	\N	0	0	0.00		2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
327237	\N	Dan	Charhut	4580	4431	2025-06-24 19:48:54.333136-05	nndz-WkMrNnhMcjdqQT09	4514	t	\N	0	0	0.00		2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
327238	\N	John	Collins	4580	4431	2025-06-24 19:48:54.333136-05	nndz-WkMrOXlMMzZnUT09	4514	t	\N	0	0	0.00		2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
327239	\N	Liam	Connell	4580	4431	2025-06-24 19:48:54.333136-05	nndz-WkMrOXlMMzloQT09	4514	t	\N	0	0	0.00		2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
327240	\N	Bob	Crawford	4580	4431	2025-06-24 19:48:54.333136-05	nndz-WkMrOXlMMzVqQT09	4514	t	\N	0	0	0.00		2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
327241	\N	Chuck	Czerkawski	4580	4431	2025-06-24 19:48:54.333136-05	nndz-WlNhd3liYjVodz09	4514	t	\N	0	0	0.00		2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
327242	\N	Eric	Daliere	4580	4431	2025-06-24 19:48:54.333136-05	nndz-WkMrOXlMMzdnQT09	4514	t	\N	1	0	100.00		2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
327243	\N	Michael	Ellis	4580	4431	2025-06-24 19:48:54.333136-05	nndz-WkMrOXlMMzlndz09	4514	t	\N	0	0	0.00		2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
327244	\N	Gil	Fitzgerald	4580	4431	2025-06-24 19:48:54.333136-05	nndz-WkMrNnhMcjhnZz09	4514	t	\N	0	0	0.00		2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
327245	\N	Andrew	Fluri	4580	4431	2025-06-24 19:48:54.333136-05	nndz-WkMrOXlMMzVodz09	4514	t	\N	1	0	100.00		2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
327246	\N	Hayden	Friese	4580	4431	2025-06-24 19:48:54.333136-05	nndz-WlNhd3libnhqQT09	4514	t	\N	0	0	0.00		2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
327247	\N	Pat	Gorand	4580	4431	2025-06-24 19:48:54.333136-05	nndz-WkMrOXlMMzhoQT09	4514	t	\N	0	0	0.00		2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
327248	\N	Jeff	Greenbury	4580	4431	2025-06-24 19:48:54.333136-05	nndz-WkMrOXlMMzdqQT09	4514	t	\N	0	0	0.00		2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
327249	\N	Will	Gruetzmacher	4580	4431	2025-06-24 19:48:54.333136-05	nndz-WkMrOXlMMzhqQT09	4514	t	\N	0	0	0.00		2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
327250	\N	Sean	Henrick	4580	4431	2025-06-24 19:48:54.333136-05	nndz-WkMrOXlMMzhnUT09	4514	t	\N	0	0	0.00		2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
327251	\N	Jim	Ipema	4580	4431	2025-06-24 19:48:54.333136-05	nndz-WkMrOXlMMzZodz09	4514	t	\N	0	0	0.00		2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
327252	\N	Hob	Jordan	4580	4431	2025-06-24 19:48:54.333136-05	nndz-WkMrOXlMMzdnZz09	4514	t	\N	0	0	0.00		2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
327253	\N	Guto	Ken Ghidini	4580	4431	2025-06-24 19:48:54.333136-05	nndz-WlNhd3libndqQT09	4514	t	\N	0	0	0.00		2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
327254	\N	Tom	Kinzer	4580	4431	2025-06-24 19:48:54.333136-05	nndz-WkMrOXlMMzhnZz09	4514	t	\N	0	0	0.00		2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
327255	\N	John	Knox	4580	4431	2025-06-24 19:48:54.333136-05	nndz-WkMrOXlMMzZnZz09	4514	t	\N	0	0	0.00		2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
327256	\N	Jorgen	Kokke	4580	4431	2025-06-24 19:48:54.333136-05	nndz-WkMrOXlMMzZqUT09	4514	t	\N	0	0	0.00		2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
327257	\N	John	Larson	4580	4431	2025-06-24 19:48:54.333136-05	nndz-WkMrOXlMMzZnQT09	4514	t	\N	0	0	0.00		2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
327258	\N	Dennis	Lingle	4580	4431	2025-06-24 19:48:54.333136-05	nndz-WkMrOXlMMzdoZz09	4514	t	\N	0	0	0.00		2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
327259	\N	Josh	Mallamud	4580	4431	2025-06-24 19:48:54.333136-05	nndz-WkMrOXlMMzZqQT09	4514	t	\N	0	0	0.00		2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
327260	\N	Raymond	Marciano	4580	4431	2025-06-24 19:48:54.333136-05	nndz-WkMrOXlMajdnQT09	4514	t	\N	0	1	0.00		2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
327261	\N	Gavin	McCoulough	4580	4431	2025-06-24 19:48:54.333136-05	nndz-WkMrOHg3ajZnZz09	4514	t	\N	0	0	0.00		2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
327262	\N	Rob	McIntire	4580	4431	2025-06-24 19:48:54.333136-05	nndz-WlNhd3liYjVoQT09	4514	t	\N	0	1	0.00		2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
327263	\N	Michael	Riback	4580	4431	2025-06-24 19:48:54.333136-05	nndz-WkMrOXlMMzlnZz09	4514	t	\N	0	0	0.00		2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
327264	\N	Jim	Seymour	4580	4431	2025-06-24 19:48:54.333136-05	nndz-WkMrOXlMMzZoZz09	4514	t	\N	0	0	0.00		2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
327265	\N	Jacob	Sheehan	4580	4431	2025-06-24 19:48:54.333136-05	nndz-WkMrOXlMMzdqUT09	4514	t	\N	0	0	0.00		2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
327266	\N	Oliver	Silver	4580	4431	2025-06-24 19:48:54.333136-05	nndz-WkMrOHg3ajZndz09	4514	t	\N	0	0	0.00		2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
327267	\N	Tod	Skarecky	4580	4431	2025-06-24 19:48:54.333136-05	nndz-WkMrOXlMMzhndz09	4514	t	\N	0	0	0.00		2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
327268	\N	Nicholas	Stec	4580	4431	2025-06-24 19:48:54.333136-05	nndz-WkMrOXlMMzhoUT09	4514	t	\N	0	0	0.00		2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
327269	\N	Brian	Stecko	4580	4431	2025-06-24 19:48:54.333136-05	nndz-WkMrOXlMMzRoUT09	4514	t	\N	0	0	0.00		2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
327270	\N	Michael	Sullivan	4580	4431	2025-06-24 19:48:54.333136-05	nndz-WkMrOXlMMzlqUT09	4514	t	\N	1	0	100.00		2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
327271	\N	Jeff	Torosian	4580	4431	2025-06-24 19:48:54.333136-05	nndz-WkMrOXlMMzZoUT09	4514	t	\N	0	0	0.00		2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
327272	\N	Matt	Williams	4580	4431	2025-06-24 19:48:54.333136-05	nndz-WkMrOXlMMzlnUT09	4514	t	\N	0	0	0.00		2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
327273	\N	David	Frye	4580	4431	2025-06-24 19:48:54.333136-05	nndz-WkMrOXlMMzdodz09	4514	t	\N	0	0	0.00		2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
327274	\N	Dave	Johnson	4580	4431	2025-06-24 19:48:54.333136-05	nndz-WkMrOXlMMzdoUT09	4514	t	\N	0	0	0.00		2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
327275	\N	Mike	Rahaley	4580	4431	2025-06-24 19:48:54.333136-05	nndz-WkMrOXhyajRoZz09	4514	t	\N	0	0	0.00		2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
327276	\N	Mike	Saliba	4580	4431	2025-06-24 19:48:54.333136-05	nndz-WkMrOXlMMzlqQT09	4514	t	\N	0	0	0.00		2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
327277	\N	Mark	Stec	4580	4431	2025-06-24 19:48:54.333136-05	nndz-WkMrOXlMMzlodz09	4514	t	\N	0	0	0.00		2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
327278	\N	Steve	Swanson	4580	4431	2025-06-24 19:48:54.333136-05	nndz-WkMrNnhMMzhnZz09	4514	t	\N	0	0	0.00		2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
327279	\N	scott	smith	4610	4431	2025-06-24 19:48:54.333136-05	nndz-WkMrNnhMdjZqUT09	4514	t	\N	0	0	0.00	CC	2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
327280	\N	Jeff	Aronoff	4610	4431	2025-06-24 19:48:54.333136-05	nndz-WkMrNng3L3hqUT09	4514	t	\N	0	0	0.00		2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
327281	\N	Ruben	Avila	4610	4431	2025-06-24 19:48:54.333136-05	nndz-WlNhd3hyYjhqUT09	4514	t	\N	0	0	0.00		2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
327282	\N	Ron	Bernstein	4610	4431	2025-06-24 19:48:54.333136-05	nndz-WkMrNnhMYjZqUT09	4514	t	\N	0	0	0.00		2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
327283	\N	David	Borovsky	4610	4431	2025-06-24 19:48:54.333136-05	nndz-WkMrNng3NzZodz09	4514	t	\N	0	0	0.00		2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
327284	\N	Michael	Brailov	4610	4431	2025-06-24 19:48:54.333136-05	nndz-WkMrNng3Ny9qQT09	4514	t	\N	0	0	0.00		2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
327285	\N	Cliff	Breslow	4610	4431	2025-06-24 19:48:54.333136-05	nndz-WlNlNXg3YjVoUT09	4514	t	\N	0	0	0.00		2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
327286	\N	Joe	Castriano	4610	4431	2025-06-24 19:48:54.333136-05	nndz-WkMrOXlMditoQT09	4514	t	\N	0	0	0.00		2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
327287	\N	Aaron	Cohn	4610	4431	2025-06-24 19:48:54.333136-05	nndz-WkMrOHdyZjZoZz09	4514	t	\N	1	0	100.00		2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
327288	\N	George	Costakis	4610	4431	2025-06-24 19:48:54.333136-05	nndz-WkMrNng3LzZqUT09	4514	t	\N	0	0	0.00		2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
327289	\N	Brad	Dennison	4610	4431	2025-06-24 19:48:54.333136-05	nndz-WkMrOXlMdjhoZz09	4514	t	\N	0	0	0.00		2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
327290	\N	David	Donenberg	4610	4431	2025-06-24 19:48:54.333136-05	nndz-WkMrOHdMNzhnQT09	4514	t	\N	0	0	0.00		2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
327291	\N	Daniel	Dorfman	4610	4431	2025-06-24 19:48:54.333136-05	nndz-WkMrOXlMajVoZz09	4514	t	\N	0	0	0.00		2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
327292	\N	Scott	Drury	4610	4431	2025-06-24 19:48:54.333136-05	nndz-WkMrNnhMcjVnUT09	4514	t	\N	0	0	0.00		2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
327293	\N	dnitry	edelchik	4610	4431	2025-06-24 19:48:54.333136-05	nndz-WkMrOXlMZi9oZz09	4514	t	\N	0	0	0.00		2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
327294	\N	Steve	Ewaldz	4610	4431	2025-06-24 19:48:54.333136-05	nndz-WkMrNnhMMzloQT09	4514	t	\N	0	1	0.00		2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
327295	\N	Brett	Fenton	4610	4431	2025-06-24 19:48:54.333136-05	nndz-WkMrNnhMajZndz09	4514	t	\N	0	0	0.00		2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
327296	\N	David	Fetter	4610	4431	2025-06-24 19:48:54.333136-05	nndz-WkMrNng3ei9nZz09	4514	t	\N	0	0	0.00		2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
327297	\N	Rich	Foss	4610	4431	2025-06-24 19:48:54.333136-05	nndz-WkMrOXliZjdnZz09	4514	t	\N	1	0	100.00		2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
327298	\N	Jeff	Fried	4610	4431	2025-06-24 19:48:54.333136-05	nndz-WkMrOXlMditqQT09	4514	t	\N	0	0	0.00		2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
327299	\N	Bruce	Friedman	4610	4431	2025-06-24 19:48:54.333136-05	nndz-WkMrOXlMdjhnUT09	4514	t	\N	0	0	0.00		2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
327300	\N	Bruce	Friedman	4610	4431	2025-06-24 19:48:54.333136-05	nndz-WlNhd3liNzhqQT09	4514	t	\N	0	1	0.00		2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
327301	\N	Chris	Gair	4610	4431	2025-06-24 19:48:54.333136-05	nndz-WkMrNng3eitoZz09	4514	t	\N	0	0	0.00		2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
327302	\N	Tim	Giardina	4610	4431	2025-06-24 19:48:54.333136-05	nndz-WlNhd3liNy9oZz09	4514	t	\N	0	0	0.00		2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
327303	\N	Dav	Graham	4610	4431	2025-06-24 19:48:54.333136-05	nndz-WkMrOXlMdnhoUT09	4514	t	\N	0	0	0.00		2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
327304	\N	Brian	Hagaman	4610	4431	2025-06-24 19:48:54.333136-05	nndz-WkMrOXlMdjlqUT09	4514	t	\N	0	0	0.00		2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
327305	\N	Adam	Heiman	4610	4431	2025-06-24 19:48:54.333136-05	nndz-WkMrNng3Ny9nUT09	4514	t	\N	0	1	0.00		2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
327306	\N	Jigs	Jvora	4610	4431	2025-06-24 19:48:54.333136-05	nndz-WlNlNXg3YjRqUT09	4514	t	\N	0	0	0.00		2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
327307	\N	Steve	Kanner	4610	4431	2025-06-24 19:48:54.333136-05	nndz-WkMrNng3Ny9odz09	4514	t	\N	0	0	0.00		2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
327308	\N	Koji	Kato	4610	4431	2025-06-24 19:48:54.333136-05	nndz-WkMrNng3ejRqQT09	4514	t	\N	0	0	0.00		2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
327309	\N	Roy	Kessel	4610	4431	2025-06-24 19:48:54.333136-05	nndz-WkMrNng3NzdqQT09	4514	t	\N	1	0	100.00		2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
327310	\N	Ivan	Kovacevic	4610	4431	2025-06-24 19:48:54.333136-05	nndz-WkMrOXlMajVnQT09	4514	t	\N	0	0	0.00		2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
327311	\N	Allen	Krissberg	4610	4431	2025-06-24 19:48:54.333136-05	nndz-WkMrNng3ei9qUT09	4514	t	\N	0	0	0.00		2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
327312	\N	Marc	Le Beau	4610	4431	2025-06-24 19:48:54.333136-05	nndz-WkMrOHdidjZqQT09	4514	t	\N	1	0	100.00		2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
327313	\N	Tom	Levy	4610	4431	2025-06-24 19:48:54.333136-05	nndz-WkMrOXlMdjhodz09	4514	t	\N	0	0	0.00		2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
327314	\N	Paul	Leyderman	4610	4431	2025-06-24 19:48:54.333136-05	nndz-WkMrNng3Nytodz09	4514	t	\N	0	1	0.00		2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
327315	\N	Phil	Macke	4610	4431	2025-06-24 19:48:54.333136-05	nndz-WkMrOHdMajZoUT09	4514	t	\N	0	0	0.00		2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
327316	\N	Howard	Martino	4610	4431	2025-06-24 19:48:54.333136-05	nndz-WkMrOXlMajVndz09	4514	t	\N	0	0	0.00		2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
327317	\N	Brian	May	4610	4431	2025-06-24 19:48:54.333136-05	nndz-WkMrOHdMZjhndz09	4514	t	\N	0	0	0.00		2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
327318	\N	Steve	Mesirow	4610	4431	2025-06-24 19:48:54.333136-05	nndz-WlNhd3lMdjVoZz09	4514	t	\N	0	0	0.00		2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
327319	\N	Greg	Meyer	4610	4431	2025-06-24 19:48:54.333136-05	nndz-WkMrNng3LzZqQT09	4514	t	\N	0	0	0.00		2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
327320	\N	Geoff	Miller	4610	4431	2025-06-24 19:48:54.333136-05	nndz-WkMrNng3Ny9nQT09	4514	t	\N	0	0	0.00		2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
327321	\N	Steve	Milstein	4610	4431	2025-06-24 19:48:54.333136-05	nndz-WkMrNng3Ly9nQT09	4514	t	\N	0	0	0.00		2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
327322	\N	Matt	Newman	4610	4431	2025-06-24 19:48:54.333136-05	nndz-WkMrNng3eitoQT09	4514	t	\N	0	0	0.00		2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
327323	\N	Greg	Orloff	4610	4431	2025-06-24 19:48:54.333136-05	nndz-WlNhd3liNy9oQT09	4514	t	\N	0	0	0.00		2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
327324	\N	Abe	Reese	4610	4431	2025-06-24 19:48:54.333136-05	nndz-WkMrNng3NytoQT09	4514	t	\N	0	0	0.00		2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
327325	\N	Mark	Ricciardi	4610	4431	2025-06-24 19:48:54.333136-05	nndz-WkMrNng3eitodz09	4514	t	\N	0	0	0.00		2025-06-24 19:48:54.333136-05	0	0	0	0.00	\N
327326	\N	Dan	Romanoff	4610	4431	2025-06-24 19:48:54.581559-05	nndz-WkMrNng3eitoUT09	4514	t	\N	1	1	50.00		2025-06-24 19:48:54.581559-05	0	0	0	0.00	\N
327327	\N	Marc	Samson	4610	4431	2025-06-24 19:48:54.581559-05	nndz-WkMrOXlibitndz09	4514	t	\N	0	0	0.00		2025-06-24 19:48:54.581559-05	0	0	0	0.00	\N
327328	\N	Brett	Saunders	4610	4431	2025-06-24 19:48:54.581559-05	nndz-WkMrOXlMYitoUT09	4514	t	\N	0	0	0.00		2025-06-24 19:48:54.581559-05	0	0	0	0.00	\N
327329	\N	Erik	Schmidt	4610	4431	2025-06-24 19:48:54.581559-05	nndz-WkMrOXlMajVodz09	4514	t	\N	0	0	0.00		2025-06-24 19:48:54.581559-05	0	0	0	0.00	\N
327330	\N	Brad	Schulman	4610	4431	2025-06-24 19:48:54.581559-05	nndz-WkMrNnhMYjZqQT09	4514	t	\N	0	0	0.00		2025-06-24 19:48:54.581559-05	0	0	0	0.00	\N
327331	\N	Phil	Seiden	4610	4431	2025-06-24 19:48:54.581559-05	nndz-WkMrOHhicjVoUT09	4514	t	\N	0	0	0.00		2025-06-24 19:48:54.581559-05	0	0	0	0.00	\N
327332	\N	Ted	Sherman	4610	4431	2025-06-24 19:48:54.581559-05	nndz-WkMrNng3ei9qQT09	4514	t	\N	0	0	0.00		2025-06-24 19:48:54.581559-05	0	0	0	0.00	\N
327333	\N	Ron	Sklare	4610	4431	2025-06-24 19:48:54.581559-05	nndz-WlNhd3lMZjVoUT09	4514	t	\N	0	0	0.00		2025-06-24 19:48:54.581559-05	0	0	0	0.00	\N
327334	\N	Rick	Spurgeon	4610	4431	2025-06-24 19:48:54.581559-05	nndz-WkMrNng3eitnUT09	4514	t	\N	0	0	0.00		2025-06-24 19:48:54.581559-05	0	0	0	0.00	\N
327335	\N	Brett	Starkopf	4610	4431	2025-06-24 19:48:54.581559-05	nndz-WkMrOHhicjVoQT09	4514	t	\N	0	0	0.00		2025-06-24 19:48:54.581559-05	0	0	0	0.00	\N
327336	\N	sebastiaan	Stoove	4610	4431	2025-06-24 19:48:54.581559-05	nndz-WlNhd3lMMzhqUT09	4514	t	\N	0	0	0.00		2025-06-24 19:48:54.581559-05	0	0	0	0.00	\N
327337	\N	Tom	Stotter	4610	4431	2025-06-24 19:48:54.581559-05	nndz-WlNhd3liNzhqUT09	4514	t	\N	1	0	100.00		2025-06-24 19:48:54.581559-05	0	0	0	0.00	\N
327338	\N	Randy	Strickley	4610	4431	2025-06-24 19:48:54.581559-05	nndz-WlNhd3hyYjZnZz09	4514	t	\N	0	0	0.00		2025-06-24 19:48:54.581559-05	0	0	0	0.00	\N
327339	\N	John	Stuparitz	4610	4431	2025-06-24 19:48:54.581559-05	nndz-WkMrNnhMYjVnQT09	4514	t	\N	0	0	0.00		2025-06-24 19:48:54.581559-05	0	0	0	0.00	\N
327340	\N	Bill	Swartz	4610	4431	2025-06-24 19:48:54.581559-05	nndz-WkMrNng3Ny9oQT09	4514	t	\N	0	0	0.00		2025-06-24 19:48:54.581559-05	0	0	0	0.00	\N
327341	\N	Christian	Trujillo	4610	4431	2025-06-24 19:48:54.581559-05	nndz-WkMrOXlMdjhnQT09	4514	t	\N	0	0	0.00		2025-06-24 19:48:54.581559-05	0	0	0	0.00	\N
327342	\N	Vijay	Vijaykumar	4610	4431	2025-06-24 19:48:54.581559-05	nndz-WlNhd3hyYitoZz09	4514	t	\N	1	0	100.00		2025-06-24 19:48:54.581559-05	0	0	0	0.00	\N
327343	\N	Aaron	Walsh	4610	4431	2025-06-24 19:48:54.581559-05	nndz-WkMrNng3cjRnUT09	4514	t	\N	0	0	0.00		2025-06-24 19:48:54.581559-05	0	0	0	0.00	\N
327344	\N	Jim	Waters	4610	4431	2025-06-24 19:48:54.581559-05	nndz-WkMrOHhidjdodz09	4514	t	\N	0	0	0.00		2025-06-24 19:48:54.581559-05	0	0	0	0.00	\N
327345	\N	Mitch	Weinstein	4610	4431	2025-06-24 19:48:54.581559-05	nndz-WkMrOXlMdjhndz09	4514	t	\N	0	0	0.00		2025-06-24 19:48:54.581559-05	0	0	0	0.00	\N
327346	\N	Justin	Wellen	4610	4431	2025-06-24 19:48:54.581559-05	nndz-WkMrOXlMajVqUT09	4514	t	\N	0	0	0.00		2025-06-24 19:48:54.581559-05	0	0	0	0.00	\N
327347	\N	Jim	Field	4612	4431	2025-06-24 19:48:54.581559-05	nndz-WkMrNnhMditnUT09	4514	t	\N	0	1	0.00	C	2025-06-24 19:48:54.581559-05	0	0	0	0.00	\N
327348	\N	Jon	Romick	4612	4431	2025-06-24 19:48:54.581559-05	nndz-WkMrNnhMbjhndz09	4514	t	\N	0	0	0.00	CC	2025-06-24 19:48:54.581559-05	0	0	0	0.00	\N
327349	\N	Drew	Barnett	4612	4431	2025-06-24 19:48:54.581559-05	nndz-WlNhd3hycjhodz09	4514	t	\N	0	0	0.00		2025-06-24 19:48:54.581559-05	0	0	0	0.00	\N
327350	\N	Scott	Becker	4612	4431	2025-06-24 19:48:54.581559-05	nndz-WkMrNnhMcndoZz09	4514	t	\N	0	1	0.00		2025-06-24 19:48:54.581559-05	0	0	0	0.00	\N
327351	\N	Marc	Blum	4612	4431	2025-06-24 19:48:54.581559-05	nndz-WkMrNnhMdjZodz09	4514	t	\N	0	1	0.00		2025-06-24 19:48:54.581559-05	0	0	0	0.00	\N
327352	\N	Dan	Borstein	4612	4431	2025-06-24 19:48:54.581559-05	nndz-WkMrNnhMbjhqQT09	4514	t	\N	0	0	0.00		2025-06-24 19:48:54.581559-05	0	0	0	0.00	\N
327353	\N	Jason	Canel	4612	4431	2025-06-24 19:48:54.581559-05	nndz-WkMrNnhMdjhoQT09	4514	t	\N	0	1	0.00		2025-06-24 19:48:54.581559-05	0	0	0	0.00	\N
327354	\N	Mark	Coe	4612	4431	2025-06-24 19:48:54.581559-05	nndz-WkMrNnhMZi9ndz09	4514	t	\N	0	0	0.00		2025-06-24 19:48:54.581559-05	0	0	0	0.00	\N
327355	\N	Roger	Daniel	4612	4431	2025-06-24 19:48:54.581559-05	nndz-WlNhd3hycjhoUT09	4514	t	\N	0	1	0.00		2025-06-24 19:48:54.581559-05	0	0	0	0.00	\N
327356	\N	Ron	Diamond	4612	4431	2025-06-24 19:48:54.581559-05	nndz-WkMrNnhMbitoUT09	4514	t	\N	0	0	0.00		2025-06-24 19:48:54.581559-05	0	0	0	0.00	\N
327357	\N	Tim	Donohue	4612	4431	2025-06-24 19:48:54.581559-05	nndz-WlNhd3hycjhoZz09	4514	t	\N	0	0	0.00		2025-06-24 19:48:54.581559-05	0	0	0	0.00	\N
327358	\N	Bruce	Ettelson	4612	4431	2025-06-24 19:48:54.581559-05	nndz-WkMrNnhMdjlqQT09	4514	t	\N	0	0	0.00		2025-06-24 19:48:54.581559-05	0	0	0	0.00	\N
327359	\N	Derek	Fish	4612	4431	2025-06-24 19:48:54.581559-05	nndz-WlNhd3hycjlqUT09	4514	t	\N	0	0	0.00		2025-06-24 19:48:54.581559-05	0	0	0	0.00	\N
327360	\N	Jim	Glikin	4612	4431	2025-06-24 19:48:54.581559-05	nndz-WkMrNnhMcjlndz09	4514	t	\N	0	0	0.00		2025-06-24 19:48:54.581559-05	0	0	0	0.00	\N
327361	\N	Daniel	Goldberg	4612	4431	2025-06-24 19:48:54.581559-05	nndz-WkMrNnhMcjhoZz09	4514	t	\N	0	1	0.00		2025-06-24 19:48:54.581559-05	0	0	0	0.00	\N
327362	\N	Jack	Goldberg	4612	4431	2025-06-24 19:48:54.581559-05	nndz-WkMrNnhMcjhnUT09	4514	t	\N	0	0	0.00		2025-06-24 19:48:54.581559-05	0	0	0	0.00	\N
327363	\N	Rob	Goldsmith	4612	4431	2025-06-24 19:48:54.581559-05	nndz-WkMrNnhMbi9oUT09	4514	t	\N	0	1	0.00		2025-06-24 19:48:54.581559-05	0	0	0	0.00	\N
327364	\N	TJ	Gordon	4612	4431	2025-06-24 19:48:54.581559-05	nndz-WkMrNnhMdjhnUT09	4514	t	\N	0	0	0.00		2025-06-24 19:48:54.581559-05	0	0	0	0.00	\N
327365	\N	Dan	Klaff	4612	4431	2025-06-24 19:48:54.581559-05	nndz-WlNhd3hycjhoQT09	4514	t	\N	0	0	0.00		2025-06-24 19:48:54.581559-05	0	0	0	0.00	\N
327366	\N	Ted	Koenig	4612	4431	2025-06-24 19:48:54.581559-05	nndz-WkMrNnhMZjdnUT09	4514	t	\N	0	0	0.00		2025-06-24 19:48:54.581559-05	0	0	0	0.00	\N
327367	\N	Adam	Kroll	4612	4431	2025-06-24 19:48:54.581559-05	nndz-WkMrOHliejZodz09	4514	t	\N	0	1	0.00		2025-06-24 19:48:54.581559-05	0	0	0	0.00	\N
327368	\N	Bradley	Lederer	4612	4431	2025-06-24 19:48:54.581559-05	nndz-WkMrNnhMdndoQT09	4514	t	\N	0	0	0.00		2025-06-24 19:48:54.581559-05	0	0	0	0.00	\N
327369	\N	Ryan	Lederer	4612	4431	2025-06-24 19:48:54.581559-05	nndz-WkMrNnhMdnhnQT09	4514	t	\N	0	0	0.00		2025-06-24 19:48:54.581559-05	0	0	0	0.00	\N
327370	\N	Steve	Levin	4612	4431	2025-06-24 19:48:54.581559-05	nndz-WkMrNnhMbjVodz09	4514	t	\N	0	0	0.00		2025-06-24 19:48:54.581559-05	0	0	0	0.00	\N
327371	\N	Marc	Monyek	4612	4431	2025-06-24 19:48:54.581559-05	nndz-WlNhd3hybnhnZz09	4514	t	\N	0	0	0.00		2025-06-24 19:48:54.581559-05	0	0	0	0.00	\N
327372	\N	Eliot	Moskow	4612	4431	2025-06-24 19:48:54.581559-05	nndz-WkMrNnhMdjlqUT09	4514	t	\N	0	0	0.00		2025-06-24 19:48:54.581559-05	0	0	0	0.00	\N
327373	\N	Matthew	Patinkin	4612	4431	2025-06-24 19:48:54.581559-05	nndz-WkMrNnhMcjlqQT09	4514	t	\N	0	0	0.00		2025-06-24 19:48:54.581559-05	0	0	0	0.00	\N
327374	\N	Keith	Radner	4612	4431	2025-06-24 19:48:54.581559-05	nndz-WkMrNnhMZjdnQT09	4514	t	\N	0	0	0.00		2025-06-24 19:48:54.581559-05	0	0	0	0.00	\N
327375	\N	Max	Reiswerg	4612	4431	2025-06-24 19:48:54.581559-05	nndz-WkMrNnhMbi9qQT09	4514	t	\N	0	0	0.00		2025-06-24 19:48:54.581559-05	0	0	0	0.00	\N
327376	\N	Dan	Rosenberg	4612	4431	2025-06-24 19:48:54.581559-05	nndz-WkMrNnhMbjRnZz09	4514	t	\N	0	0	0.00		2025-06-24 19:48:54.581559-05	0	0	0	0.00	\N
327377	\N	Sami	Rosenblatt	4612	4431	2025-06-24 19:48:54.581559-05	nndz-WkMrNnhMbi9qUT09	4514	t	\N	0	0	0.00		2025-06-24 19:48:54.581559-05	0	0	0	0.00	\N
327378	\N	Steve	Schaumburger	4612	4431	2025-06-24 19:48:54.581559-05	nndz-WkMrNnhMbi9nQT09	4514	t	\N	0	1	0.00		2025-06-24 19:48:54.581559-05	0	0	0	0.00	\N
327379	\N	Dave	Stafman	4612	4431	2025-06-24 19:48:54.581559-05	nndz-WkMrNnhMdjhoZz09	4514	t	\N	0	0	0.00		2025-06-24 19:48:54.581559-05	0	0	0	0.00	\N
327380	\N	Tommy	Sternberg	4612	4431	2025-06-24 19:48:54.581559-05	nndz-WkMrOHhyLytqUT09	4514	t	\N	0	0	0.00		2025-06-24 19:48:54.581559-05	0	0	0	0.00	\N
327381	\N	Dan	Tresley	4612	4431	2025-06-24 19:48:54.581559-05	nndz-WkMrNnhMditndz09	4514	t	\N	0	0	0.00		2025-06-24 19:48:54.581559-05	0	0	0	0.00	\N
327382	\N	Ryan	Turf	4612	4431	2025-06-24 19:48:54.581559-05	nndz-WkMrOHhyL3hoQT09	4514	t	\N	0	0	0.00		2025-06-24 19:48:54.581559-05	0	0	0	0.00	\N
327383	\N	Doug	Warshauer	4612	4431	2025-06-24 19:48:54.581559-05	nndz-WkMrNnhMcjlqUT09	4514	t	\N	0	1	0.00		2025-06-24 19:48:54.581559-05	0	0	0	0.00	\N
327384	\N	Joe	Yastrow	4612	4431	2025-06-24 19:48:54.581559-05	nndz-WlNhd3hycjlqQT09	4514	t	\N	0	0	0.00		2025-06-24 19:48:54.581559-05	0	0	0	0.00	\N
327385	\N	Brian	Scullion	4616	4431	2025-06-24 19:48:54.581559-05	nndz-WkMrNnhMajdoUT09	4514	t	\N	0	1	0.00	C	2025-06-24 19:48:54.581559-05	0	0	0	0.00	\N
327386	\N	Rob	Balon	4616	4431	2025-06-24 19:48:54.581559-05	nndz-WkMrNng3LzdnZz09	4514	t	\N	0	0	0.00	CC	2025-06-24 19:48:54.581559-05	0	0	0	0.00	\N
327387	\N	Hank	Baby	4616	4431	2025-06-24 19:48:54.581559-05	nndz-WkMrNnhMdjRnUT09	4514	t	\N	0	0	0.00		2025-06-24 19:48:54.581559-05	0	0	0	0.00	\N
327388	\N	Scott	Baby	4616	4431	2025-06-24 19:48:54.581559-05	nndz-WkMrNnhMcnhoQT09	4514	t	\N	0	0	0.00		2025-06-24 19:48:54.581559-05	0	0	0	0.00	\N
327389	\N	Larry	Barr	4616	4431	2025-06-24 19:48:54.581559-05	nndz-WkMrNnhMbjRndz09	4514	t	\N	1	0	100.00		2025-06-24 19:48:54.581559-05	0	0	0	0.00	\N
327390	\N	Romie	Castelli	4616	4431	2025-06-24 19:48:54.581559-05	nndz-WkMrNnhMdjRnQT09	4514	t	\N	0	0	0.00		2025-06-24 19:48:54.581559-05	0	0	0	0.00	\N
327391	\N	Mike	Cavalier	4616	4431	2025-06-24 19:48:54.581559-05	nndz-WkMrNnhMajVnUT09	4514	t	\N	0	0	0.00		2025-06-24 19:48:54.581559-05	0	0	0	0.00	\N
327392	\N	James	Costello	4616	4431	2025-06-24 19:48:54.581559-05	nndz-WlNhd3hydndndz09	4514	t	\N	0	0	0.00		2025-06-24 19:48:54.581559-05	0	0	0	0.00	\N
327393	\N	Doug	Crimmins	4616	4431	2025-06-24 19:48:54.581559-05	nndz-WkMrNnhMZjVnUT09	4514	t	\N	0	0	0.00		2025-06-24 19:48:54.581559-05	0	0	0	0.00	\N
327394	\N	Scott	Ellis	4616	4431	2025-06-24 19:48:54.581559-05	nndz-WkMrNng3LzdnUT09	4514	t	\N	0	1	0.00		2025-06-24 19:48:54.581559-05	0	0	0	0.00	\N
327395	\N	Bryan	Foley	4616	4431	2025-06-24 19:48:54.581559-05	nndz-WkMrNnhMcnhodz09	4514	t	\N	0	0	0.00		2025-06-24 19:48:54.581559-05	0	0	0	0.00	\N
327396	\N	Scott	Frerichs	4616	4431	2025-06-24 19:48:54.581559-05	nndz-WkMrNnhMYitnQT09	4514	t	\N	0	0	0.00		2025-06-24 19:48:54.581559-05	0	0	0	0.00	\N
327397	\N	Bill	Frothingham	4616	4431	2025-06-24 19:48:54.581559-05	nndz-WkMrNng3Lzdndz09	4514	t	\N	0	1	0.00		2025-06-24 19:48:54.581559-05	0	0	0	0.00	\N
327398	\N	Waldo	Herrera	4616	4431	2025-06-24 19:48:54.581559-05	nndz-WkMrNng3ejlqQT09	4514	t	\N	0	0	0.00		2025-06-24 19:48:54.581559-05	0	0	0	0.00	\N
327399	\N	Keith	Kenner	4616	4431	2025-06-24 19:48:54.581559-05	nndz-WkMrNnhMYjlodz09	4514	t	\N	0	0	0.00		2025-06-24 19:48:54.581559-05	0	0	0	0.00	\N
327400	\N	Jeff	Meisles	4616	4431	2025-06-24 19:48:54.581559-05	nndz-WkMrNng3ejhoUT09	4514	t	\N	0	1	0.00		2025-06-24 19:48:54.581559-05	0	0	0	0.00	\N
327401	\N	John	Mooney	4616	4431	2025-06-24 19:48:54.581559-05	nndz-WlNhd3hydndqUT09	4514	t	\N	0	0	0.00		2025-06-24 19:48:54.581559-05	0	0	0	0.00	\N
327402	\N	Joel	Moses	4616	4431	2025-06-24 19:48:54.581559-05	nndz-WkMrNng3ejhoQT09	4514	t	\N	0	0	0.00		2025-06-24 19:48:54.581559-05	0	0	0	0.00	\N
327403	\N	Mike	Nolan	4616	4431	2025-06-24 19:48:54.581559-05	nndz-WkMrNng3LzdqUT09	4514	t	\N	0	0	0.00		2025-06-24 19:48:54.581559-05	0	0	0	0.00	\N
327404	\N	Derek	van der Vorst	4616	4431	2025-06-24 19:48:54.581559-05	nndz-WkMrOXlMcjRoUT09	4514	t	\N	1	0	100.00		2025-06-24 19:48:54.581559-05	0	0	0	0.00	\N
327405	\N	Steve	Kennett	4635	4431	2025-06-24 19:48:54.581559-05	nndz-WkMrNnhMdndoZz09	4514	t	\N	0	0	0.00	C	2025-06-24 19:48:54.581559-05	0	0	0	0.00	\N
327406	\N	Ricky	Abt	4635	4431	2025-06-24 19:48:54.581559-05	nndz-WkMrNnhMdjVndz09	4514	t	\N	0	1	0.00		2025-06-24 19:48:54.581559-05	0	0	0	0.00	\N
327407	\N	Jim	Baird	4635	4431	2025-06-24 19:48:54.581559-05	nndz-WkMrNng3NzdoZz09	4514	t	\N	0	0	0.00		2025-06-24 19:48:54.581559-05	0	0	0	0.00	\N
327408	\N	Chuck	Boehrer	4635	4431	2025-06-24 19:48:54.581559-05	nndz-WkMrNnhMM3hnQT09	4514	t	\N	0	0	0.00		2025-06-24 19:48:54.581559-05	0	0	0	0.00	\N
327409	\N	RJ	Bukovac	4635	4431	2025-06-24 19:48:54.581559-05	nndz-WkMrNnhMci9oZz09	4514	t	\N	0	0	0.00		2025-06-24 19:48:54.581559-05	0	0	0	0.00	\N
327410	\N	Michael	Cornelo	4635	4431	2025-06-24 19:48:54.581559-05	nndz-WkMrNnhMajdoQT09	4514	t	\N	0	0	0.00		2025-06-24 19:48:54.581559-05	0	0	0	0.00	\N
327411	\N	John	Croghan	4635	4431	2025-06-24 19:48:54.581559-05	nndz-WkMrNng3NzZnQT09	4514	t	\N	1	0	100.00		2025-06-24 19:48:54.581559-05	0	0	0	0.00	\N
327412	\N	Fritz	Duda	4635	4431	2025-06-24 19:48:54.581559-05	nndz-WkMrNng3Ly9nUT09	4514	t	\N	0	0	0.00		2025-06-24 19:48:54.581559-05	0	0	0	0.00	\N
327413	\N	Erik	Falk	4635	4431	2025-06-24 19:48:54.581559-05	nndz-WlNhd3liNzdoUT09	4514	t	\N	0	0	0.00		2025-06-24 19:48:54.581559-05	0	0	0	0.00	\N
327414	\N	Kevin	Frid	4635	4431	2025-06-24 19:48:54.581559-05	nndz-WkMrNnhMcjZndz09	4514	t	\N	0	1	0.00		2025-06-24 19:48:54.581559-05	0	0	0	0.00	\N
327415	\N	Gordon	Gluckman	4635	4431	2025-06-24 19:48:54.581559-05	nndz-WkMrNnhMdjloUT09	4514	t	\N	0	0	0.00		2025-06-24 19:48:54.581559-05	0	0	0	0.00	\N
327416	\N	Bill	Hague	4635	4431	2025-06-24 19:48:54.581559-05	nndz-WkMrNnhMbjZqUT09	4514	t	\N	0	1	0.00		2025-06-24 19:48:54.581559-05	0	0	0	0.00	\N
327417	\N	Steve	Hansen	4635	4431	2025-06-24 19:48:54.581559-05	nndz-WkMrNnhMM3dndz09	4514	t	\N	0	0	0.00		2025-06-24 19:48:54.581559-05	0	0	0	0.00	\N
327418	\N	Arthur	Holden	4635	4431	2025-06-24 19:48:54.581559-05	nndz-WkMrNnhMM3hoQT09	4514	t	\N	0	0	0.00		2025-06-24 19:48:54.581559-05	0	0	0	0.00	\N
327419	\N	Brad	Jaros	4635	4431	2025-06-24 19:48:54.581559-05	nndz-WkMrNnhMdjVqUT09	4514	t	\N	0	0	0.00		2025-06-24 19:48:54.581559-05	0	0	0	0.00	\N
327420	\N	Bob	Kaspers	4635	4431	2025-06-24 19:48:54.581559-05	nndz-WkMrNnhMZjVnQT09	4514	t	\N	0	0	0.00		2025-06-24 19:48:54.581559-05	0	0	0	0.00	\N
327421	\N	Jack	Keller	4635	4431	2025-06-24 19:48:54.581559-05	nndz-WkMrNng3ejVoZz09	4514	t	\N	0	0	0.00		2025-06-24 19:48:54.581559-05	0	0	0	0.00	\N
327422	\N	John	Levert	4635	4431	2025-06-24 19:48:54.581559-05	nndz-WkMrOHdiL3dqQT09	4514	t	\N	1	0	100.00		2025-06-24 19:48:54.581559-05	0	0	0	0.00	\N
327423	\N	Bruce	Mackinnon	4635	4431	2025-06-24 19:48:54.581559-05	nndz-WkMrNng3cjZnUT09	4514	t	\N	0	1	0.00		2025-06-24 19:48:54.581559-05	0	0	0	0.00	\N
327424	\N	Rich	McManiman	4635	4431	2025-06-24 19:48:54.581559-05	nndz-WkMrOHdiejVoQT09	4514	t	\N	0	0	0.00		2025-06-24 19:48:54.581559-05	0	0	0	0.00	\N
327425	\N	Paget	Neave	4635	4431	2025-06-24 19:48:54.581559-05	nndz-WkMrOXliMy9ndz09	4514	t	\N	0	0	0.00		2025-06-24 19:48:54.581559-05	0	0	0	0.00	\N
327426	\N	Garett	Nesbitt	4635	4431	2025-06-24 19:48:54.581559-05	nndz-WkMrNnhMYjloUT09	4514	t	\N	0	0	0.00		2025-06-24 19:48:54.581559-05	0	0	0	0.00	\N
327427	\N	Michael	OBrien	4635	4431	2025-06-24 19:48:54.581559-05	nndz-WkMrNnhMbndqUT09	4514	t	\N	2	0	100.00		2025-06-24 19:48:54.581559-05	0	0	0	0.00	\N
327428	\N	Keegan	O’Brian	4635	4431	2025-06-24 19:48:54.581559-05	nndz-WkMrOHc3NzZoQT09	4514	t	\N	1	0	100.00		2025-06-24 19:48:54.581559-05	0	0	0	0.00	\N
327429	\N	Jeff	Ramsay	4635	4431	2025-06-24 19:48:54.581559-05	nndz-WkMrNnhMdjRoUT09	4514	t	\N	0	0	0.00		2025-06-24 19:48:54.581559-05	0	0	0	0.00	\N
327430	\N	Greg	Robitaille	4635	4431	2025-06-24 19:48:54.581559-05	nndz-WkMrNng3NytqUT09	4514	t	\N	0	0	0.00		2025-06-24 19:48:54.581559-05	0	0	0	0.00	\N
327431	\N	Evan	Rudy	4635	4431	2025-06-24 19:48:54.581559-05	nndz-WkMrNng3NytnZz09	4514	t	\N	0	0	0.00		2025-06-24 19:48:54.581559-05	0	0	0	0.00	\N
327432	\N	Bob	Soudan	4635	4431	2025-06-24 19:48:54.581559-05	nndz-WkMrNnhMZjVndz09	4514	t	\N	0	0	0.00		2025-06-24 19:48:54.581559-05	0	0	0	0.00	\N
327433	\N	Steve	Steger	4635	4431	2025-06-24 19:48:54.581559-05	nndz-WkMrNnhMcjZoUT09	4514	t	\N	0	0	0.00		2025-06-24 19:48:54.581559-05	0	0	0	0.00	\N
327434	\N	Sean	Sullivan	4635	4431	2025-06-24 19:48:54.581559-05	nndz-WkMrNnhMZndoZz09	4514	t	\N	0	0	0.00		2025-06-24 19:48:54.581559-05	0	0	0	0.00	\N
327435	\N	Dan	Walsh	4635	4431	2025-06-24 19:48:54.581559-05	nndz-WkMrNnhMcjRnZz09	4514	t	\N	0	0	0.00		2025-06-24 19:48:54.581559-05	0	0	0	0.00	\N
327436	\N	Matt	Warrd	4635	4431	2025-06-24 19:48:54.581559-05	nndz-WkMrNng3cjZnQT09	4514	t	\N	0	1	0.00		2025-06-24 19:48:54.581559-05	0	0	0	0.00	\N
327437	\N	Bruce	Williamson	4635	4431	2025-06-24 19:48:54.581559-05	nndz-WkMrNnhMM3hnZz09	4514	t	\N	0	1	0.00		2025-06-24 19:48:54.581559-05	0	0	0	0.00	\N
327438	\N	Bill	Young	4635	4431	2025-06-24 19:48:54.581559-05	nndz-WkMrNng3ejdoQT09	4514	t	\N	0	0	0.00		2025-06-24 19:48:54.581559-05	0	0	0	0.00	\N
327439	\N	Greg	Gaffen	4638	4431	2025-06-24 19:48:54.581559-05	nndz-WkMrNnhMbnhnZz09	4514	t	\N	1	0	100.00	C	2025-06-24 19:48:54.581559-05	0	0	0	0.00	\N
327440	\N	Bryan	Benavidas	4638	4431	2025-06-24 19:48:54.581559-05	nndz-WkMrNng3MzlnZz09	4514	t	\N	1	0	100.00		2025-06-24 19:48:54.581559-05	0	0	0	0.00	\N
327441	\N	Evan	Budin	4638	4431	2025-06-24 19:48:54.581559-05	nndz-WlNhd3hMYitnQT09	4514	t	\N	1	0	100.00		2025-06-24 19:48:54.581559-05	0	0	0	0.00	\N
327442	\N	Jason	Dubinsky	4638	4431	2025-06-24 19:48:54.581559-05	nndz-WkMrOXliejhndz09	4514	t	\N	1	0	100.00		2025-06-24 19:48:54.581559-05	0	0	0	0.00	\N
327443	\N	Brian	Dunn	4638	4431	2025-06-24 19:48:54.581559-05	nndz-WlNhd3hMYitqUT09	4514	t	\N	0	0	0.00		2025-06-24 19:48:54.581559-05	0	0	0	0.00	\N
327444	\N	Seth	Hopkins	4638	4431	2025-06-24 19:48:54.581559-05	nndz-WkMrNng3ejhnZz09	4514	t	\N	0	0	0.00		2025-06-24 19:48:54.581559-05	0	0	0	0.00	\N
327445	\N	Eric	Kalman	4638	4431	2025-06-24 19:48:54.581559-05	nndz-WlNhd3hMYitndz09	4514	t	\N	1	0	100.00		2025-06-24 19:48:54.581559-05	0	0	0	0.00	\N
327446	\N	Jim	Levitas	4638	4431	2025-06-24 19:48:54.581559-05	nndz-WlNhd3hMYnhoUT09	4514	t	\N	1	0	100.00		2025-06-24 19:48:54.581559-05	0	0	0	0.00	\N
327447	\N	Mike	McCarthy	4638	4431	2025-06-24 19:48:54.581559-05	nndz-WkMrNng3ejdqQT09	4514	t	\N	1	0	100.00		2025-06-24 19:48:54.581559-05	0	0	0	0.00	\N
327448	\N	Paul	Patt	4638	4431	2025-06-24 19:48:54.581559-05	nndz-WkMrNng3ejhqUT09	4514	t	\N	1	0	100.00		2025-06-24 19:48:54.581559-05	0	0	0	0.00	\N
327449	\N	Kevin	Ryan	4638	4431	2025-06-24 19:48:54.581559-05	nndz-WkMrOHc3ZnhnUT09	4514	t	\N	1	0	100.00		2025-06-24 19:48:54.581559-05	0	0	0	0.00	\N
327450	\N	Jamie	Silverman	4638	4431	2025-06-24 19:48:54.581559-05	nndz-WkMrOXliejhqUT09	4514	t	\N	1	0	100.00		2025-06-24 19:48:54.581559-05	0	0	0	0.00	\N
327451	\N	Stan	Vajdic	4638	4431	2025-06-24 19:48:54.581559-05	nndz-WkMrNng3ei9oUT09	4514	t	\N	0	0	0.00		2025-06-24 19:48:54.581559-05	0	0	0	0.00	\N
327452	\N	John	Velkme	4638	4431	2025-06-24 19:48:54.581559-05	nndz-WkMrNng3NzhnQT09	4514	t	\N	0	0	0.00		2025-06-24 19:48:54.581559-05	0	0	0	0.00	\N
327453	\N	Rob	Werman	4638	4431	2025-06-24 19:48:54.581559-05	nndz-WlNld3g3bnhoQT09	4514	t	\N	0	0	0.00		2025-06-24 19:48:54.581559-05	0	0	0	0.00	\N
327454	\N	Adam	Morgan	4571	4432	2025-06-24 19:48:54.581559-05	nndz-WkMrNng3Nytndz09	4514	t	\N	1	0	100.00	C	2025-06-24 19:48:54.581559-05	0	0	0	0.00	\N
327455	\N	Brad	Berish	4571	4432	2025-06-24 19:48:54.581559-05	nndz-WkMrNnhMbjdoZz09	4514	t	\N	1	1	50.00		2025-06-24 19:48:54.581559-05	0	0	0	0.00	\N
327456	\N	Ben	Bronson	4571	4432	2025-06-24 19:48:54.581559-05	nndz-WlNTNXhMcnhndz09	4514	t	\N	0	1	0.00		2025-06-24 19:48:54.581559-05	0	0	0	0.00	\N
327457	\N	Andrew	Brown	4571	4432	2025-06-24 19:48:54.581559-05	nndz-WkMrNnhMdi9ndz09	4514	t	\N	0	2	0.00		2025-06-24 19:48:54.581559-05	0	0	0	0.00	\N
327458	\N	Ethan	Cantor	4571	4432	2025-06-24 19:48:54.581559-05	nndz-WkMrNng3NzloZz09	4514	t	\N	1	0	100.00		2025-06-24 19:48:54.581559-05	0	0	0	0.00	\N
327459	\N	Lowell	Cantor	4571	4432	2025-06-24 19:48:54.581559-05	nndz-WkMrOHdManhodz09	4514	t	\N	1	0	100.00		2025-06-24 19:48:54.581559-05	0	0	0	0.00	\N
327460	\N	Daniel	Dolgin	4571	4432	2025-06-24 19:48:54.581559-05	nndz-WkMrNng3M3hqUT09	4514	t	\N	0	2	0.00		2025-06-24 19:48:54.581559-05	0	0	0	0.00	\N
327461	\N	Zach	Domont	4571	4432	2025-06-24 19:48:54.581559-05	nndz-WlNTNXhiajdndz09	4514	t	\N	0	1	0.00		2025-06-24 19:48:54.581559-05	0	0	0	0.00	\N
327462	\N	Brad	Dworkin	4571	4432	2025-06-24 19:48:54.581559-05	nndz-WkMrNnhMZjRndz09	4514	t	\N	0	0	0.00		2025-06-24 19:48:54.581559-05	0	0	0	0.00	\N
327463	\N	Carl	Gatenio	4571	4432	2025-06-24 19:48:54.581559-05	nndz-WlNTNXhiajdnZz09	4514	t	\N	0	1	0.00		2025-06-24 19:48:54.581559-05	0	0	0	0.00	\N
327464	\N	Greg	Goldsmith	4571	4432	2025-06-24 19:48:54.581559-05	nndz-WkMrNnhMZjlnZz09	4514	t	\N	0	0	0.00		2025-06-24 19:48:54.581559-05	0	0	0	0.00	\N
327465	\N	Steve	Goodman	4571	4432	2025-06-24 19:48:54.581559-05	nndz-WkMrNnhMcjlnQT09	4514	t	\N	0	0	0.00		2025-06-24 19:48:54.581559-05	0	0	0	0.00	\N
327466	\N	Marc	Kallish	4571	4432	2025-06-24 19:48:54.581559-05	nndz-WkMrNnhMdi9nZz09	4514	t	\N	0	0	0.00		2025-06-24 19:48:54.581559-05	0	0	0	0.00	\N
327467	\N	Adam	Kaplan	4571	4432	2025-06-24 19:48:54.581559-05	nndz-WkMrNng3enhoZz09	4514	t	\N	1	1	50.00		2025-06-24 19:48:54.581559-05	0	0	0	0.00	\N
327468	\N	Larry	Kaskel	4571	4432	2025-06-24 19:48:54.581559-05	nndz-WkMrNnhMZjhqQT09	4514	t	\N	1	0	100.00		2025-06-24 19:48:54.581559-05	0	0	0	0.00	\N
327469	\N	Mort	Kessel	4571	4432	2025-06-24 19:48:54.581559-05	nndz-WkMrNnhMai9ndz09	4514	t	\N	1	1	50.00		2025-06-24 19:48:54.581559-05	0	0	0	0.00	\N
327470	\N	Jeremy	Knobel	4571	4432	2025-06-24 19:48:54.581559-05	nndz-WkMrNng3MytnUT09	4514	t	\N	0	1	0.00		2025-06-24 19:48:54.581559-05	0	0	0	0.00	\N
327471	\N	Eric	Kuby	4571	4432	2025-06-24 19:48:54.581559-05	nndz-WlNTNXhiajZoZz09	4514	t	\N	1	1	50.00		2025-06-24 19:48:54.581559-05	0	0	0	0.00	\N
327472	\N	Paul	Morton	4571	4432	2025-06-24 19:48:54.581559-05	nndz-WkMrNnhMMzZqUT09	4514	t	\N	1	1	50.00		2025-06-24 19:48:54.581559-05	0	0	0	0.00	\N
327473	\N	Matt	Nadell	4571	4432	2025-06-24 19:48:54.581559-05	nndz-WlNTNXhiajdnQT09	4514	t	\N	1	0	100.00		2025-06-24 19:48:54.581559-05	0	0	0	0.00	\N
327474	\N	Adam	Posner	4571	4432	2025-06-24 19:48:54.581559-05	nndz-WkMrNnhMajZnUT09	4514	t	\N	1	0	100.00		2025-06-24 19:48:54.581559-05	0	0	0	0.00	\N
327475	\N	Adam	Sheppard	4571	4432	2025-06-24 19:48:54.581559-05	nndz-WkMrOHdyMzVqUT09	4514	t	\N	0	1	0.00		2025-06-24 19:48:54.581559-05	0	0	0	0.00	\N
327476	\N	Rick	Goldman	4571	4432	2025-06-24 19:48:54.581559-05	nndz-WkMrNnhMZjRqQT09	4514	t	\N	0	0	0.00		2025-06-24 19:48:54.581559-05	0	0	0	0.00	\N
327477	\N	Harlan	Kahn	4571	4432	2025-06-24 19:48:54.581559-05	nndz-WkMrNnhMdi9qUT09	4514	t	\N	0	0	0.00		2025-06-24 19:48:54.581559-05	0	0	0	0.00	\N
327478	\N	Jim	Kirsch	4571	4432	2025-06-24 19:48:54.581559-05	nndz-WkMrNnhMbjZoZz09	4514	t	\N	0	0	0.00		2025-06-24 19:48:54.581559-05	0	0	0	0.00	\N
327479	\N	David	Kleifield	4571	4432	2025-06-24 19:48:54.581559-05	nndz-WkMrOHdMLzdnUT09	4514	t	\N	0	0	0.00		2025-06-24 19:48:54.581559-05	0	0	0	0.00	\N
327480	\N	Howard	Klieger	4571	4432	2025-06-24 19:48:54.581559-05	nndz-WkMrNnhMai9oZz09	4514	t	\N	0	0	0.00		2025-06-24 19:48:54.581559-05	0	0	0	0.00	\N
327481	\N	Scott	Lassar	4571	4432	2025-06-24 19:48:54.581559-05	nndz-WkMrNnhMdjRodz09	4514	t	\N	0	0	0.00		2025-06-24 19:48:54.581559-05	0	0	0	0.00	\N
327482	\N	Jeff	Nathanson	4571	4432	2025-06-24 19:48:54.581559-05	nndz-WkMrNnhMdjhnQT09	4514	t	\N	0	0	0.00		2025-06-24 19:48:54.581559-05	0	0	0	0.00	\N
327483	\N	Bruce	Pinsof	4571	4432	2025-06-24 19:48:54.581559-05	nndz-WkMrNnhMajloQT09	4514	t	\N	0	1	0.00		2025-06-24 19:48:54.581559-05	0	0	0	0.00	\N
327484	\N	Jonathan	Quinn	4571	4432	2025-06-24 19:48:54.581559-05	nndz-WkMrNnhMcjVoZz09	4514	t	\N	0	0	0.00		2025-06-24 19:48:54.581559-05	0	0	0	0.00	\N
327485	\N	Rob	Rabin	4571	4432	2025-06-24 19:48:54.581559-05	nndz-WkMrNnhMMzloUT09	4514	t	\N	0	0	0.00		2025-06-24 19:48:54.581559-05	0	0	0	0.00	\N
327486	\N	Ken	Small	4571	4432	2025-06-24 19:48:54.581559-05	nndz-WkMrNnhMdjRoQT09	4514	t	\N	0	0	0.00		2025-06-24 19:48:54.581559-05	0	0	0	0.00	\N
327487	\N	John	Looby	4600	4432	2025-06-24 19:48:54.581559-05	nndz-WkMrNnhMajRoZz09	4514	t	\N	1	1	50.00	C	2025-06-24 19:48:54.581559-05	0	0	0	0.00	\N
327488	\N	Rob	Bentley	4600	4432	2025-06-24 19:48:54.581559-05	nndz-WkMrNng3LzZodz09	4514	t	\N	1	1	50.00	CC	2025-06-24 19:48:54.581559-05	0	0	0	0.00	\N
327489	\N	Rob	Busam	4600	4432	2025-06-24 19:48:54.581559-05	nndz-WkMrNng3NzRodz09	4514	t	\N	1	1	50.00		2025-06-24 19:48:54.581559-05	0	0	0	0.00	\N
327490	\N	Steve	Carver	4600	4432	2025-06-24 19:48:54.581559-05	nndz-WkMrNng3cjRoQT09	4514	t	\N	0	0	0.00		2025-06-24 19:48:54.581559-05	0	0	0	0.00	\N
327491	\N	Hunter	Gordy	4600	4432	2025-06-24 19:48:54.581559-05	nndz-WkMrNng3LzZoQT09	4514	t	\N	1	0	100.00		2025-06-24 19:48:54.581559-05	0	0	0	0.00	\N
327492	\N	Glenn	Heidbreder	4600	4432	2025-06-24 19:48:54.581559-05	nndz-WkMrNnhMandqUT09	4514	t	\N	0	0	0.00		2025-06-24 19:48:54.581559-05	0	0	0	0.00	\N
327493	\N	David	Hunt	4600	4432	2025-06-24 19:48:54.581559-05	nndz-WkMrNng3LzZoZz09	4514	t	\N	1	0	100.00		2025-06-24 19:48:54.581559-05	0	0	0	0.00	\N
327494	\N	Alex	Kane	4600	4432	2025-06-24 19:48:54.581559-05	nndz-WlNhd3hyandnUT09	4514	t	\N	2	0	100.00		2025-06-24 19:48:54.581559-05	0	0	0	0.00	\N
327495	\N	Will	Lindquist	4600	4432	2025-06-24 19:48:54.581559-05	nndz-WkMrOXlMbjlnZz09	4514	t	\N	0	1	0.00		2025-06-24 19:48:54.581559-05	0	0	0	0.00	\N
327496	\N	Mike	McClelland	4600	4432	2025-06-24 19:48:54.581559-05	nndz-WkMrNng3LzZoUT09	4514	t	\N	2	0	100.00		2025-06-24 19:48:54.581559-05	0	0	0	0.00	\N
327497	\N	Ted	North	4600	4432	2025-06-24 19:48:54.581559-05	nndz-WkMrNng3MzZnZz09	4514	t	\N	0	0	0.00		2025-06-24 19:48:54.581559-05	0	0	0	0.00	\N
327498	\N	Andy	Pfahl	4600	4432	2025-06-24 19:48:54.581559-05	nndz-WkMrOXlMbjlqQT09	4514	t	\N	1	0	100.00		2025-06-24 19:48:54.581559-05	0	0	0	0.00	\N
327499	\N	Pat	Priola	4600	4432	2025-06-24 19:48:54.581559-05	nndz-WkMrNng3endnZz09	4514	t	\N	1	1	50.00		2025-06-24 19:48:54.581559-05	0	0	0	0.00	\N
327500	\N	Tim	Richmond	4600	4432	2025-06-24 19:48:54.581559-05	nndz-WkMrNng3Mytndz09	4514	t	\N	0	1	0.00		2025-06-24 19:48:54.581559-05	0	0	0	0.00	\N
327501	\N	Jack	Schwab	4600	4432	2025-06-24 19:48:54.581559-05	nndz-WlNld3hyNzhodz09	4514	t	\N	0	1	0.00		2025-06-24 19:48:54.581559-05	0	0	0	0.00	\N
327502	\N	Paul	Sundberg	4600	4432	2025-06-24 19:48:54.581559-05	nndz-WkMrNnhMYjVoQT09	4514	t	\N	1	0	100.00		2025-06-24 19:48:54.581559-05	0	0	0	0.00	\N
327503	\N	Corey	Burd	4600	4432	2025-06-24 19:48:54.581559-05	nndz-WkMrNng3endoZz09	4514	t	\N	1	0	100.00		2025-06-24 19:48:54.581559-05	0	0	0	0.00	\N
327504	\N	Mike	Church	4600	4432	2025-06-24 19:48:54.581559-05	nndz-WlNld3hyNy9qUT09	4514	t	\N	0	0	0.00		2025-06-24 19:48:54.581559-05	0	0	0	0.00	\N
327505	\N	Josh	Clifford	4600	4432	2025-06-24 19:48:54.581559-05	nndz-WlNld3hyNy9qQT09	4514	t	\N	0	0	0.00		2025-06-24 19:48:54.581559-05	0	0	0	0.00	\N
327506	\N	Ted	Constantine	4600	4432	2025-06-24 19:48:54.581559-05	nndz-WkMrNnhMYitndz09	4514	t	\N	0	1	0.00		2025-06-24 19:48:54.581559-05	0	0	0	0.00	\N
327507	\N	Jay	Edwards	4600	4432	2025-06-24 19:48:54.581559-05	nndz-WkMrNnhMajVoZz09	4514	t	\N	1	0	100.00		2025-06-24 19:48:54.581559-05	0	0	0	0.00	\N
327508	\N	Ben	Gauthier	4600	4432	2025-06-24 19:48:54.581559-05	nndz-WkMrNnhMYnhoQT09	4514	t	\N	1	1	50.00		2025-06-24 19:48:54.581559-05	0	0	0	0.00	\N
327509	\N	John	Gescheidle	4600	4432	2025-06-24 19:48:54.581559-05	nndz-WkMrOHhidjdndz09	4514	t	\N	0	0	0.00		2025-06-24 19:48:54.581559-05	0	0	0	0.00	\N
327510	\N	Randy	Hara	4600	4432	2025-06-24 19:48:54.581559-05	nndz-WlNhd3hyanhoUT09	4514	t	\N	0	0	0.00		2025-06-24 19:48:54.581559-05	0	0	0	0.00	\N
327511	\N	Gam	Huggins	4600	4432	2025-06-24 19:48:54.581559-05	nndz-WkMrNng3endnUT09	4514	t	\N	0	0	0.00		2025-06-24 19:48:54.581559-05	0	0	0	0.00	\N
327512	\N	Brian	Kelley	4600	4432	2025-06-24 19:48:54.581559-05	nndz-WlNhd3hyanhnUT09	4514	t	\N	0	1	0.00		2025-06-24 19:48:54.581559-05	0	0	0	0.00	\N
327513	\N	Doug	Lee	4600	4432	2025-06-24 19:48:54.581559-05	nndz-WkMrNng3LzdqQT09	4514	t	\N	0	1	0.00		2025-06-24 19:48:54.581559-05	0	0	0	0.00	\N
327514	\N	Tom	Lesko	4600	4432	2025-06-24 19:48:54.581559-05	nndz-WkMrNnhMYjlqQT09	4514	t	\N	1	0	100.00		2025-06-24 19:48:54.581559-05	0	0	0	0.00	\N
327515	\N	Kevin	Lewis	4600	4432	2025-06-24 19:48:54.581559-05	nndz-WlNhd3hyaitoZz09	4514	t	\N	1	0	100.00		2025-06-24 19:48:54.581559-05	0	0	0	0.00	\N
327516	\N	Karl	Lorenz	4600	4432	2025-06-24 19:48:54.581559-05	nndz-WkMrOHhidjdnUT09	4514	t	\N	0	1	0.00		2025-06-24 19:48:54.581559-05	0	0	0	0.00	\N
327517	\N	Pete	Martens	4600	4432	2025-06-24 19:48:54.581559-05	nndz-WkMrNnhMYnhodz09	4514	t	\N	1	0	100.00		2025-06-24 19:48:54.581559-05	0	0	0	0.00	\N
327518	\N	Todd	Ozog	4600	4432	2025-06-24 19:48:54.581559-05	nndz-WkMrOHlMejZnUT09	4514	t	\N	0	0	0.00		2025-06-24 19:48:54.581559-05	0	0	0	0.00	\N
327519	\N	Quentin	Pelser	4600	4432	2025-06-24 19:48:54.581559-05	nndz-WlNhd3hyanhoQT09	4514	t	\N	0	0	0.00		2025-06-24 19:48:54.581559-05	0	0	0	0.00	\N
327520	\N	Jason	Perlioni	4600	4432	2025-06-24 19:48:54.581559-05	nndz-WlNld3hydjlndz09	4514	t	\N	0	0	0.00		2025-06-24 19:48:54.581559-05	0	0	0	0.00	\N
327521	\N	Travis	Raebel	4600	4432	2025-06-24 19:48:54.581559-05	nndz-WkMrOHlMejZoZz09	4514	t	\N	1	0	100.00		2025-06-24 19:48:54.581559-05	0	0	0	0.00	\N
327522	\N	Bruce	Rylance	4600	4432	2025-06-24 19:48:54.581559-05	nndz-WkMrNnhMdjhndz09	4514	t	\N	0	0	0.00		2025-06-24 19:48:54.581559-05	0	0	0	0.00	\N
327523	\N	Marc	Silver	4600	4432	2025-06-24 19:48:54.581559-05	nndz-WkMrNnhMZjlodz09	4514	t	\N	1	0	100.00		2025-06-24 19:48:54.581559-05	0	0	0	0.00	\N
327524	\N	Michael	Tracy	4600	4432	2025-06-24 19:48:54.581559-05	nndz-WkMrNng3NzRoZz09	4514	t	\N	0	0	0.00		2025-06-24 19:48:54.581559-05	0	0	0	0.00	\N
327525	\N	Dan	Wagener	4600	4432	2025-06-24 19:48:54.581559-05	nndz-WlNhd3hyanhoZz09	4514	t	\N	0	0	0.00		2025-06-24 19:48:54.581559-05	0	0	0	0.00	\N
327526	\N	Don	Williams	4600	4432	2025-06-24 19:48:54.581559-05	nndz-WkMrOHhidjdoZz09	4514	t	\N	0	0	0.00		2025-06-24 19:48:54.581559-05	0	0	0	0.00	\N
327527	\N	Christopher	Young	4600	4432	2025-06-24 19:48:54.581559-05	nndz-WkMrNnhMajRodz09	4514	t	\N	1	0	100.00		2025-06-24 19:48:54.581559-05	0	0	0	0.00	\N
327528	\N	Matt	Young	4600	4432	2025-06-24 19:48:54.581559-05	nndz-WlNhd3hyanhodz09	4514	t	\N	1	0	100.00		2025-06-24 19:48:54.581559-05	0	0	0	0.00	\N
327529	\N	Larry	Schechtman	4623	4432	2025-06-24 19:48:54.581559-05	nndz-WkMrNnhMcjhqQT09	4514	t	\N	1	1	50.00	C	2025-06-24 19:48:54.581559-05	0	0	0	0.00	\N
327530	\N	Ted	Gilbert	4623	4432	2025-06-24 19:48:54.581559-05	nndz-WkMrNnhMMzZodz09	4514	t	\N	0	1	0.00	CC	2025-06-24 19:48:54.581559-05	0	0	0	0.00	\N
327531	\N	Michael	Baritz	4623	4432	2025-06-24 19:48:54.581559-05	nndz-WkMrNnhMbjZoUT09	4514	t	\N	0	0	0.00		2025-06-24 19:48:54.581559-05	0	0	0	0.00	\N
327532	\N	Stuart	Boynton	4623	4432	2025-06-24 19:48:54.581559-05	nndz-WlNlNXc3Lzdodz09	4514	t	\N	0	0	0.00		2025-06-24 19:48:54.581559-05	0	0	0	0.00	\N
327533	\N	Bruce	Brown	4623	4432	2025-06-24 19:48:54.581559-05	nndz-WkMrNng3MzloUT09	4514	t	\N	0	0	0.00		2025-06-24 19:48:54.581559-05	0	0	0	0.00	\N
327534	\N	Jared	Burstein	4623	4432	2025-06-24 19:48:54.581559-05	nndz-WlNld3lMandqQT09	4514	t	\N	0	0	0.00		2025-06-24 19:48:54.581559-05	0	0	0	0.00	\N
327535	\N	Jared	Burstein	4623	4432	2025-06-24 19:48:54.581559-05	nndz-WlNld3lMYjZoZz09	4514	t	\N	1	0	100.00		2025-06-24 19:48:54.581559-05	0	0	0	0.00	\N
327536	\N	Scott	Busse	4623	4432	2025-06-24 19:48:54.581559-05	nndz-WkMrNnhMYjZnZz09	4514	t	\N	0	0	0.00		2025-06-24 19:48:54.581559-05	0	0	0	0.00	\N
327537	\N	Jason	Chess	4623	4432	2025-06-24 19:48:54.581559-05	nndz-WlNlNXlibnhqQT09	4514	t	\N	0	1	0.00		2025-06-24 19:48:54.581559-05	0	0	0	0.00	\N
327538	\N	Chad	Coe	4623	4432	2025-06-24 19:48:54.581559-05	nndz-WkMrNnhMajlqUT09	4514	t	\N	1	0	100.00		2025-06-24 19:48:54.581559-05	0	0	0	0.00	\N
327539	\N	Adam	Docks	4623	4432	2025-06-24 19:48:54.581559-05	nndz-WkMrNng3N3dndz09	4514	t	\N	0	1	0.00		2025-06-24 19:48:54.581559-05	0	0	0	0.00	\N
327540	\N	Dan	Dorfman	4623	4432	2025-06-24 19:48:54.581559-05	nndz-WlNhd3liLy9nQT09	4514	t	\N	0	0	0.00		2025-06-24 19:48:54.581559-05	0	0	0	0.00	\N
327541	\N	Steve	Edelson	4623	4432	2025-06-24 19:48:54.581559-05	nndz-WkMrNnhMditoZz09	4514	t	\N	0	0	0.00		2025-06-24 19:48:54.581559-05	0	0	0	0.00	\N
327542	\N	Mike	Eisenberg	4623	4432	2025-06-24 19:48:54.581559-05	nndz-WkMrNnhMMytnZz09	4514	t	\N	0	0	0.00		2025-06-24 19:48:54.581559-05	0	0	0	0.00	\N
327543	\N	Stephen	Freiburn	4623	4432	2025-06-24 19:48:54.581559-05	nndz-WlNld3lMYjloUT09	4514	t	\N	0	1	0.00		2025-06-24 19:48:54.581559-05	0	0	0	0.00	\N
327544	\N	Jay	Garber	4623	4432	2025-06-24 19:48:54.581559-05	nndz-WlNld3lMYjlodz09	4514	t	\N	1	0	100.00		2025-06-24 19:48:54.581559-05	0	0	0	0.00	\N
327545	\N	Sheldon	Gelber	4623	4432	2025-06-24 19:48:54.581559-05	nndz-WkMrNng3N3dnUT09	4514	t	\N	0	0	0.00		2025-06-24 19:48:54.581559-05	0	0	0	0.00	\N
327546	\N	Barry	Goldberg	4623	4432	2025-06-24 19:48:54.581559-05	nndz-WkMrNnhMdjdqUT09	4514	t	\N	2	0	100.00		2025-06-24 19:48:54.581559-05	0	0	0	0.00	\N
327547	\N	Mel	Gottlieb	4623	4432	2025-06-24 19:48:54.581559-05	nndz-WkMrNnhMMytndz09	4514	t	\N	0	0	0.00		2025-06-24 19:48:54.581559-05	0	0	0	0.00	\N
327548	\N	Keith	Karchmar	4623	4432	2025-06-24 19:48:54.581559-05	nndz-WkMrNng3N3dnQT09	4514	t	\N	0	0	0.00		2025-06-24 19:48:54.581559-05	0	0	0	0.00	\N
327549	\N	Robert	Keller	4623	4432	2025-06-24 19:48:54.581559-05	nndz-WkMrNnhMbjZoQT09	4514	t	\N	0	2	0.00		2025-06-24 19:48:54.581559-05	0	0	0	0.00	\N
327550	\N	Glen	Kider	4623	4432	2025-06-24 19:48:54.581559-05	nndz-WkMrNng3N3hnZz09	4514	t	\N	0	0	0.00		2025-06-24 19:48:54.581559-05	0	0	0	0.00	\N
327551	\N	Dean	Klassman	4623	4432	2025-06-24 19:48:54.581559-05	nndz-WkMrNng3N3doQT09	4514	t	\N	0	0	0.00		2025-06-24 19:48:54.581559-05	0	0	0	0.00	\N
327552	\N	Lonnie	Klein	4623	4432	2025-06-24 19:48:54.581559-05	nndz-WkMrNnhMdjZoUT09	4514	t	\N	0	0	0.00		2025-06-24 19:48:54.581559-05	0	0	0	0.00	\N
327553	\N	Howard	Klieger	4623	4432	2025-06-24 19:48:54.581559-05	nndz-WlNld3lMYjZnZz09	4514	t	\N	0	1	0.00		2025-06-24 19:48:54.581559-05	0	0	0	0.00	\N
327554	\N	Jeff	Kriozere	4623	4432	2025-06-24 19:48:54.581559-05	nndz-WkMrNnhMMytqUT09	4514	t	\N	0	0	0.00		2025-06-24 19:48:54.581559-05	0	0	0	0.00	\N
327555	\N	Adam	Levine	4623	4432	2025-06-24 19:48:54.581559-05	nndz-WkMrNng3N3hqUT09	4514	t	\N	0	0	0.00		2025-06-24 19:48:54.581559-05	0	0	0	0.00	\N
327556	\N	Rich	Levine	4623	4432	2025-06-24 19:48:54.581559-05	nndz-WkMrNnhMYjZndz09	4514	t	\N	0	0	0.00		2025-06-24 19:48:54.581559-05	0	0	0	0.00	\N
327557	\N	Rich	Levine	4623	4432	2025-06-24 19:48:54.581559-05	nndz-WlNhd3liLy9nUT09	4514	t	\N	0	0	0.00		2025-06-24 19:48:54.581559-05	0	0	0	0.00	\N
327558	\N	Mark	Marvel	4623	4432	2025-06-24 19:48:54.581559-05	nndz-WkMrNng3L3hnZz09	4514	t	\N	0	0	0.00		2025-06-24 19:48:54.581559-05	0	0	0	0.00	\N
327559	\N	Jim	Mayer	4623	4432	2025-06-24 19:48:54.581559-05	nndz-WkMrNnhMdjZoQT09	4514	t	\N	0	0	0.00		2025-06-24 19:48:54.581559-05	0	0	0	0.00	\N
327560	\N	Barry	Mendel	4623	4432	2025-06-24 19:48:54.581559-05	nndz-WkMrNnhMdjdqQT09	4514	t	\N	1	0	100.00		2025-06-24 19:48:54.581559-05	0	0	0	0.00	\N
327561	\N	Ed	Newmark	4623	4432	2025-06-24 19:48:54.581559-05	nndz-WlNhd3liLy9nZz09	4514	t	\N	0	0	0.00		2025-06-24 19:48:54.581559-05	0	0	0	0.00	\N
327562	\N	Ed	Newmark	4623	4432	2025-06-24 19:48:54.581559-05	nndz-WkMrNng3N3dodz09	4514	t	\N	0	0	0.00		2025-06-24 19:48:54.581559-05	0	0	0	0.00	\N
327563	\N	Dan	Pikelny	4623	4432	2025-06-24 19:48:54.581559-05	nndz-WlNhd3liLy9oQT09	4514	t	\N	0	0	0.00		2025-06-24 19:48:54.581559-05	0	0	0	0.00	\N
327564	\N	Nikolai	Prosjanykov	4623	4432	2025-06-24 19:48:54.581559-05	nndz-WlNhd3liejlnZz09	4514	t	\N	0	0	0.00		2025-06-24 19:48:54.581559-05	0	0	0	0.00	\N
327565	\N	Jeff	Puro	4623	4432	2025-06-24 19:48:54.581559-05	nndz-WkMrNng3N3dqQT09	4514	t	\N	0	0	0.00		2025-06-24 19:48:54.581559-05	0	0	0	0.00	\N
327566	\N	Rich	Rosenberg	4623	4432	2025-06-24 19:48:54.581559-05	nndz-WlNld3lMYjZndz09	4514	t	\N	0	0	0.00		2025-06-24 19:48:54.581559-05	0	0	0	0.00	\N
327567	\N	Steve	Sacks	4623	4432	2025-06-24 19:48:54.581559-05	nndz-WlNlNXdMajRoZz09	4514	t	\N	0	0	0.00		2025-06-24 19:48:54.581559-05	0	0	0	0.00	\N
327568	\N	Steve	Safron	4623	4432	2025-06-24 19:48:54.581559-05	nndz-WkMrNnhMandnZz09	4514	t	\N	1	1	50.00		2025-06-24 19:48:54.581559-05	0	0	0	0.00	\N
327569	\N	Michael	Savitt	4623	4432	2025-06-24 19:48:54.581559-05	nndz-WkMrNng3N3hqQT09	4514	t	\N	0	0	0.00		2025-06-24 19:48:54.581559-05	0	0	0	0.00	\N
327570	\N	Rick	Schmidt	4623	4432	2025-06-24 19:48:54.581559-05	nndz-WlNld3lMYjloQT09	4514	t	\N	0	1	0.00		2025-06-24 19:48:54.581559-05	0	0	0	0.00	\N
327571	\N	Brian	Schurgin	4623	4432	2025-06-24 19:48:54.581559-05	nndz-WlNld3lMYjZqQT09	4514	t	\N	0	0	0.00		2025-06-24 19:48:54.581559-05	0	0	0	0.00	\N
327572	\N	Adam	Schwartz	4623	4432	2025-06-24 19:48:54.581559-05	nndz-WkMrNng3N3dqUT09	4514	t	\N	0	0	0.00		2025-06-24 19:48:54.581559-05	0	0	0	0.00	\N
327573	\N	Ron	Sklare	4623	4432	2025-06-24 19:48:54.581559-05	nndz-WkMrNng3N3dnZz09	4514	t	\N	0	0	0.00		2025-06-24 19:48:54.581559-05	0	0	0	0.00	\N
327574	\N	Stan	Slovin	4623	4432	2025-06-24 19:48:54.581559-05	nndz-WkMrNng3N3doZz09	4514	t	\N	0	0	0.00		2025-06-24 19:48:54.581559-05	0	0	0	0.00	\N
327575	\N	Danny	Spungen	4623	4432	2025-06-24 19:48:54.581559-05	nndz-WlNhd3liLy9qUT09	4514	t	\N	0	0	0.00		2025-06-24 19:48:54.581559-05	0	0	0	0.00	\N
327576	\N	Jason	St Onge	4623	4432	2025-06-24 19:48:54.581559-05	nndz-WlNld3lMYjZqUT09	4514	t	\N	2	0	100.00		2025-06-24 19:48:54.581559-05	0	0	0	0.00	\N
327577	\N	Jason	St. Onge	4623	4432	2025-06-24 19:48:54.581559-05	nndz-WlNhd3liLy9ndz09	4514	t	\N	0	0	0.00		2025-06-24 19:48:54.581559-05	0	0	0	0.00	\N
327578	\N	Rick	Stone	4623	4432	2025-06-24 19:48:54.581559-05	nndz-WkMrNnhMajlnZz09	4514	t	\N	0	0	0.00		2025-06-24 19:48:54.581559-05	0	0	0	0.00	\N
327579	\N	Dan	Warhaftig	4623	4432	2025-06-24 19:48:54.581559-05	nndz-WkMrNng3N3doUT09	4514	t	\N	0	0	0.00		2025-06-24 19:48:54.581559-05	0	0	0	0.00	\N
327580	\N	Jeffrey	Condren	4638	4432	2025-06-24 19:48:54.581559-05	nndz-WkMrOXliejhoZz09	4514	t	\N	2	0	100.00	C	2025-06-24 19:48:54.581559-05	0	0	0	0.00	\N
327581	\N	Ross	Freedman	4638	4432	2025-06-24 19:48:54.581559-05	nndz-WlNhd3hMYi9nQT09	4514	t	\N	1	1	50.00	CC	2025-06-24 19:48:54.581559-05	0	0	0	0.00	\N
327582	\N	Mike	Borchew	4638	4432	2025-06-24 19:48:54.581559-05	nndz-WkMrNnhMZjZoUT09	4514	t	\N	1	1	50.00		2025-06-24 19:48:54.581559-05	0	0	0	0.00	\N
327583	\N	Harold	Dawson	4638	4432	2025-06-24 19:48:54.581559-05	nndz-WkMrNnhMYjRodz09	4514	t	\N	1	0	100.00		2025-06-24 19:48:54.581559-05	0	0	0	0.00	\N
327584	\N	Ryan	Engel	4638	4432	2025-06-24 19:48:54.581559-05	nndz-WkMrNng3ejloZz09	4514	t	\N	1	1	50.00		2025-06-24 19:48:54.581559-05	0	0	0	0.00	\N
327585	\N	Victor	Forman	4638	4432	2025-06-24 19:48:54.581559-05	nndz-WlNld3libjdndz09	4514	t	\N	1	1	50.00		2025-06-24 19:48:54.581559-05	0	0	0	0.00	\N
327586	\N	Mike	Lieberman	4638	4432	2025-06-24 19:48:54.581559-05	nndz-WlNhd3hMYi9ndz09	4514	t	\N	1	0	100.00		2025-06-24 19:48:54.581559-05	0	0	0	0.00	\N
327587	\N	Greg	Pinsky	4638	4432	2025-06-24 19:48:54.581559-05	nndz-WlNhd3hMYi9qUT09	4514	t	\N	0	0	0.00		2025-06-24 19:48:54.581559-05	0	0	0	0.00	\N
327588	\N	Dan	Romanoff	4638	4432	2025-06-24 19:48:54.581559-05	nndz-WkMrNng3eitoUT09	4514	t	\N	1	1	50.00		2025-06-24 19:48:54.581559-05	0	0	0	0.00	\N
327589	\N	Ken	Samson	4638	4432	2025-06-24 19:48:54.581559-05	nndz-WkMrNng3ei9ndz09	4514	t	\N	0	1	0.00		2025-06-24 19:48:54.581559-05	0	0	0	0.00	\N
327590	\N	Bill	Sims	4638	4432	2025-06-24 19:48:54.581559-05	nndz-WkMrNnhMMytnQT09	4514	t	\N	0	1	0.00		2025-06-24 19:48:54.581559-05	0	0	0	0.00	\N
327591	\N	Eli	Strick	4638	4432	2025-06-24 19:48:54.581559-05	nndz-WlNhd3hMYi9qQT09	4514	t	\N	1	1	50.00		2025-06-24 19:48:54.581559-05	0	0	0	0.00	\N
327592	\N	Brian	Wagner	4638	4432	2025-06-24 19:48:54.581559-05	nndz-WlNhd3hMYitoUT09	4514	t	\N	2	0	100.00		2025-06-24 19:48:54.581559-05	0	0	0	0.00	\N
327593	\N	Duan	Chen	4642	4432	2025-06-24 19:48:54.581559-05	nndz-WkMrNnhMYjRnQT09	4514	t	\N	2	0	100.00	C	2025-06-24 19:48:54.581559-05	0	0	0	0.00	\N
327594	\N	John	Calkins	4642	4432	2025-06-24 19:48:54.581559-05	nndz-WkMrOHhiMzhoUT09	4514	t	\N	0	0	0.00	CC	2025-06-24 19:48:54.581559-05	0	0	0	0.00	\N
327595	\N	Alex	Bender	4642	4432	2025-06-24 19:48:54.581559-05	nndz-WlNTNXhiejdodz09	4514	t	\N	1	0	100.00		2025-06-24 19:48:54.581559-05	0	0	0	0.00	\N
327596	\N	Brian	Bowen	4642	4432	2025-06-24 19:48:54.581559-05	nndz-WlNTNXhiejdnQT09	4514	t	\N	0	0	0.00		2025-06-24 19:48:54.581559-05	0	0	0	0.00	\N
327597	\N	Sebastian	(2B) Brauer	4642	4432	2025-06-24 19:48:54.581559-05	nndz-WlNTNXhiMzRqQT09	4514	t	\N	0	0	0.00		2025-06-24 19:48:54.581559-05	0	0	0	0.00	\N
327598	\N	Werner	Camoras	4642	4432	2025-06-24 19:48:54.581559-05	nndz-WkMrNnhMbjdnZz09	4514	t	\N	2	0	100.00		2025-06-24 19:48:54.581559-05	0	0	0	0.00	\N
327599	\N	Don	Chae	4642	4432	2025-06-24 19:48:54.581559-05	nndz-WkMrNnhMYjhnUT09	4514	t	\N	1	0	100.00		2025-06-24 19:48:54.581559-05	0	0	0	0.00	\N
327600	\N	RJ	Coleman	4642	4432	2025-06-24 19:48:54.581559-05	nndz-WlNTNXhiejdqQT09	4514	t	\N	0	0	0.00		2025-06-24 19:48:54.581559-05	0	0	0	0.00	\N
327601	\N	Paul	Frischer	4642	4432	2025-06-24 19:48:54.581559-05	nndz-WlNTNXhiejZoUT09	4514	t	\N	1	0	100.00		2025-06-24 19:48:54.581559-05	0	0	0	0.00	\N
327602	\N	David	Greenfield	4642	4432	2025-06-24 19:48:54.581559-05	nndz-WlNTNXhiejdnZz09	4514	t	\N	1	0	100.00		2025-06-24 19:48:54.581559-05	0	0	0	0.00	\N
327603	\N	Dylan	Irwin	4642	4432	2025-06-24 19:48:54.581559-05	nndz-WlNTNXhiMzRnUT09	4514	t	\N	0	0	0.00		2025-06-24 19:48:54.581559-05	0	0	0	0.00	\N
327604	\N	Scott	Kirkpatrick	4642	4432	2025-06-24 19:48:54.581559-05	nndz-WlNTNXhiejZoQT09	4514	t	\N	1	0	100.00		2025-06-24 19:48:54.581559-05	0	0	0	0.00	\N
327605	\N	Bill	Leff	4642	4432	2025-06-24 19:48:54.581559-05	nndz-WlNTNXhiejZodz09	4514	t	\N	1	0	100.00		2025-06-24 19:48:54.581559-05	0	0	0	0.00	\N
327606	\N	Bob	Lepkowski	4642	4432	2025-06-24 19:48:54.581559-05	nndz-WlNTNXhiejZqQT09	4514	t	\N	0	0	0.00		2025-06-24 19:48:54.581559-05	0	0	0	0.00	\N
327607	\N	Amit	Malik	4642	4432	2025-06-24 19:48:54.581559-05	nndz-WlNTNXhiejZnUT09	4514	t	\N	0	0	0.00		2025-06-24 19:48:54.581559-05	0	0	0	0.00	\N
327608	\N	Al	Momongon	4642	4432	2025-06-24 19:48:54.581559-05	nndz-WkMrOHc3LzlnZz09	4514	t	\N	0	0	0.00		2025-06-24 19:48:54.581559-05	0	0	0	0.00	\N
327609	\N	allen	momongon	4642	4432	2025-06-24 19:48:54.581559-05	nndz-WkMrNng3NzhoUT09	4514	t	\N	0	0	0.00		2025-06-24 19:48:54.581559-05	0	0	0	0.00	\N
327610	\N	Brian	Ochab	4642	4432	2025-06-24 19:48:54.581559-05	nndz-WlNTNXhiejZnQT09	4514	t	\N	1	0	100.00		2025-06-24 19:48:54.581559-05	0	0	0	0.00	\N
327611	\N	Joe	Slaby	4642	4432	2025-06-24 19:48:54.581559-05	nndz-WkMrNnhMdjhqQT09	4514	t	\N	1	0	100.00		2025-06-24 19:48:54.581559-05	0	0	0	0.00	\N
327612	\N	Brian	Washa	4642	4432	2025-06-24 19:48:54.581559-05	nndz-WlNTNXhiejZoZz09	4514	t	\N	0	0	0.00		2025-06-24 19:48:54.581559-05	0	0	0	0.00	\N
327613	\N	Steve	Albrecht	4646	4432	2025-06-24 19:48:54.581559-05	nndz-WkMrNnhMci9ndz09	4514	t	\N	0	1	0.00	C	2025-06-24 19:48:54.581559-05	0	0	0	0.00	\N
327614	\N	Michael	Aitken	4646	4432	2025-06-24 19:48:54.581559-05	nndz-WkMrNnhMci9qQT09	4514	t	\N	1	1	50.00		2025-06-24 19:48:54.581559-05	0	0	0	0.00	\N
327615	\N	Bob	Bernstein	4646	4432	2025-06-24 19:48:54.581559-05	nndz-WlNlNXdiejhnUT09	4514	t	\N	0	2	0.00		2025-06-24 19:48:54.581559-05	0	0	0	0.00	\N
327616	\N	James	Brooks	4646	4432	2025-06-24 19:48:54.581559-05	nndz-WlNlNXdiejhodz09	4514	t	\N	0	1	0.00		2025-06-24 19:48:54.581559-05	0	0	0	0.00	\N
327617	\N	Dan	Connolly	4646	4432	2025-06-24 19:48:54.581559-05	nndz-WkMrNnhMcjdnUT09	4514	t	\N	0	0	0.00		2025-06-24 19:48:54.581559-05	0	0	0	0.00	\N
327618	\N	Jay	Dembsky	4646	4432	2025-06-24 19:48:54.581559-05	nndz-WlNlNXdiejhnQT09	4514	t	\N	0	0	0.00		2025-06-24 19:48:54.581559-05	0	0	0	0.00	\N
327619	\N	Chuck	Duffield	4646	4432	2025-06-24 19:48:54.581559-05	nndz-WlNlNXdiejlqUT09	4514	t	\N	0	1	0.00		2025-06-24 19:48:54.581559-05	0	0	0	0.00	\N
327620	\N	Michael	Edwards	4646	4432	2025-06-24 19:48:54.581559-05	nndz-WlNlNXdicitoUT09	4514	t	\N	0	1	0.00		2025-06-24 19:48:54.581559-05	0	0	0	0.00	\N
327621	\N	Pat	Fragassi	4646	4432	2025-06-24 19:48:54.581559-05	nndz-WkMrOXliMy9nUT09	4514	t	\N	0	0	0.00		2025-06-24 19:48:54.581559-05	0	0	0	0.00	\N
327622	\N	Rod	Gibbs	4646	4432	2025-06-24 19:48:54.581559-05	nndz-WkMrNnhMcjdnZz09	4514	t	\N	0	0	0.00		2025-06-24 19:48:54.581559-05	0	0	0	0.00	\N
327623	\N	Glenn	Hamrick	4646	4432	2025-06-24 19:48:54.581559-05	nndz-WlNlNXdicitoQT09	4514	t	\N	0	2	0.00		2025-06-24 19:48:54.581559-05	0	0	0	0.00	\N
327624	\N	Gary	Harman	4646	4432	2025-06-24 19:48:54.581559-05	nndz-WlNTNXhMcnhoUT09	4514	t	\N	0	0	0.00		2025-06-24 19:48:54.581559-05	0	0	0	0.00	\N
327625	\N	Mike	Horton	4646	4432	2025-06-24 19:48:54.581559-05	nndz-WlNlNXdiejlqQT09	4514	t	\N	0	1	0.00		2025-06-24 19:48:54.581559-05	0	0	0	0.00	\N
327626	\N	Sridar	Komar	4646	4432	2025-06-24 19:48:54.581559-05	nndz-WlNlNXdiejlnZz09	4514	t	\N	1	1	50.00		2025-06-24 19:48:54.581559-05	0	0	0	0.00	\N
327627	\N	Charles	Minkus	4646	4432	2025-06-24 19:48:54.581559-05	nndz-WkMrNnhMZjhndz09	4514	t	\N	0	0	0.00		2025-06-24 19:48:54.581559-05	0	0	0	0.00	\N
327628	\N	Lloyd	Morgan	4646	4432	2025-06-24 19:48:54.581559-05	nndz-WlNlNXdiejhoZz09	4514	t	\N	0	0	0.00		2025-06-24 19:48:54.581559-05	0	0	0	0.00	\N
327629	\N	Bob	Mucci	4646	4432	2025-06-24 19:48:54.581559-05	nndz-WlNlNXdiejhoUT09	4514	t	\N	0	2	0.00		2025-06-24 19:48:54.581559-05	0	0	0	0.00	\N
327630	\N	Steve	Polydoris	4646	4432	2025-06-24 19:48:54.581559-05	nndz-WlNlNXdiejhoQT09	4514	t	\N	0	2	0.00		2025-06-24 19:48:54.581559-05	0	0	0	0.00	\N
327631	\N	John	Sarkett	4646	4432	2025-06-24 19:48:54.581559-05	nndz-WkMrNnhMYjVqQT09	4514	t	\N	0	1	0.00		2025-06-24 19:48:54.581559-05	0	0	0	0.00	\N
327632	\N	Larry	Spieth	4646	4432	2025-06-24 19:48:54.581559-05	nndz-WlNlNXdMdndoUT09	4514	t	\N	0	0	0.00		2025-06-24 19:48:54.581559-05	0	0	0	0.00	\N
327633	\N	Marty	Stein	4646	4432	2025-06-24 19:48:54.581559-05	nndz-WlNTNXhMcitqQT09	4514	t	\N	0	1	0.00		2025-06-24 19:48:54.581559-05	0	0	0	0.00	\N
327634	\N	Dave	Vedder	4646	4432	2025-06-24 19:48:54.581559-05	nndz-WlNlNXdiejhndz09	4514	t	\N	0	0	0.00		2025-06-24 19:48:54.581559-05	0	0	0	0.00	\N
327635	\N	Volker	Schulmeyer	4646	4432	2025-06-24 19:48:54.581559-05	nndz-WkMrNnhMcjdodz09	4514	t	\N	0	0	0.00		2025-06-24 19:48:54.581559-05	0	0	0	0.00	\N
327636	\N	Baird	Smart	4646	4432	2025-06-24 19:48:54.581559-05	nndz-WkMrNng3M3dnUT09	4514	t	\N	0	0	0.00		2025-06-24 19:48:54.581559-05	0	0	0	0.00	\N
327637	\N	Adam	Morgan	4571	4433	2025-06-24 19:48:54.581559-05	nndz-WkMrNng3Nytndz09	4514	t	\N	1	0	100.00	C	2025-06-24 19:48:54.581559-05	0	0	0	0.00	\N
327638	\N	Birchwood	1	4571	4433	2025-06-24 19:48:54.581559-05	nndz-WlNlNXdibnhoUT09	4514	t	\N	0	0	0.00		2025-06-24 19:48:54.581559-05	0	0	0	0.00	\N
327639	\N	Birchwood	2	4571	4433	2025-06-24 19:48:54.581559-05	nndz-WlNlNXdibnhoQT09	4514	t	\N	0	0	0.00		2025-06-24 19:48:54.581559-05	0	0	0	0.00	\N
327640	\N	Adam	Cohen	4571	4433	2025-06-24 19:48:54.581559-05	nndz-WlNhd3hyNzRqUT09	4514	t	\N	1	0	100.00		2025-06-24 19:48:54.581559-05	0	0	0	0.00	\N
327641	\N	Michael	Cohen	4571	4433	2025-06-24 19:48:54.581559-05	nndz-WkMrNng3LzVoZz09	4514	t	\N	0	1	0.00		2025-06-24 19:48:54.581559-05	0	0	0	0.00	\N
327642	\N	Mike	Delrahim	4571	4433	2025-06-24 19:48:54.581559-05	nndz-WlNTNXhiajdoZz09	4514	t	\N	0	1	0.00		2025-06-24 19:48:54.581559-05	0	0	0	0.00	\N
327643	\N	Daniel	Dolgin	4571	4433	2025-06-24 19:48:54.581559-05	nndz-WkMrNng3M3hqUT09	4514	t	\N	0	2	0.00		2025-06-24 19:48:54.581559-05	0	0	0	0.00	\N
327644	\N	Jordan	Feiger	4571	4433	2025-06-24 19:48:54.581559-05	nndz-WkMrNng3M3hnZz09	4514	t	\N	0	0	0.00		2025-06-24 19:48:54.581559-05	0	0	0	0.00	\N
327645	\N	lee	frank	4571	4433	2025-06-24 19:48:54.581559-05	nndz-WkMrNnhMdjZnUT09	4514	t	\N	0	1	0.00		2025-06-24 19:48:54.581559-05	0	0	0	0.00	\N
327646	\N	Mike	Friedman	4571	4433	2025-06-24 19:48:54.581559-05	nndz-WlNTNXhiajdnUT09	4514	t	\N	0	1	0.00		2025-06-24 19:48:54.581559-05	0	0	0	0.00	\N
327647	\N	Jeff	Gordon	4571	4433	2025-06-24 19:48:54.581559-05	nndz-WkMrNnhMYi9odz09	4514	t	\N	0	0	0.00		2025-06-24 19:48:54.581559-05	0	0	0	0.00	\N
327648	\N	Todd	Grayson	4571	4433	2025-06-24 19:48:54.581559-05	nndz-WkMrNnhMajlodz09	4514	t	\N	0	2	0.00		2025-06-24 19:48:54.581559-05	0	0	0	0.00	\N
327649	\N	Andrew	Henoch	4571	4433	2025-06-24 19:48:54.581559-05	nndz-WkMrNng3MytoUT09	4514	t	\N	0	1	0.00		2025-06-24 19:48:54.581559-05	0	0	0	0.00	\N
327650	\N	Adam	Kaplan	4571	4433	2025-06-24 19:48:54.581559-05	nndz-WkMrNng3enhoZz09	4514	t	\N	1	1	50.00		2025-06-24 19:48:54.581559-05	0	0	0	0.00	\N
327651	\N	Steve	Maletzky	4571	4433	2025-06-24 19:48:54.581559-05	nndz-WkMrOHdicitoQT09	4514	t	\N	0	0	0.00		2025-06-24 19:48:54.581559-05	0	0	0	0.00	\N
327652	\N	Golan	Mor	4571	4433	2025-06-24 19:48:54.581559-05	nndz-WkMrNng3M3hqQT09	4514	t	\N	0	0	0.00		2025-06-24 19:48:54.581559-05	0	0	0	0.00	\N
327653	\N	Dylan	Rowe	4571	4433	2025-06-24 19:48:54.581559-05	nndz-WlNTNXhMcnhnZz09	4514	t	\N	0	1	0.00		2025-06-24 19:48:54.581559-05	0	0	0	0.00	\N
327654	\N	Jon	Rubenstein	4571	4433	2025-06-24 19:48:54.581559-05	nndz-WkMrNng3enhnQT09	4514	t	\N	0	1	0.00		2025-06-24 19:48:54.581559-05	0	0	0	0.00	\N
327655	\N	Michael	Schallman	4571	4433	2025-06-24 19:48:54.581559-05	nndz-WlNTNXhiajdodz09	4514	t	\N	0	1	0.00		2025-06-24 19:48:54.581559-05	0	0	0	0.00	\N
327656	\N	Charles	Auguello	4571	4433	2025-06-24 19:48:54.581559-05	nndz-WkMrNng3N3hoQT09	4514	t	\N	0	0	0.00		2025-06-24 19:48:54.581559-05	0	0	0	0.00	\N
327657	\N	Ben	Barnett	4571	4433	2025-06-24 19:48:54.581559-05	nndz-WkMrNng3N3hndz09	4514	t	\N	0	0	0.00		2025-06-24 19:48:54.581559-05	0	0	0	0.00	\N
327658	\N	Dan	Bronson	4571	4433	2025-06-24 19:48:54.581559-05	nndz-WkMrNnhMbjdodz09	4514	t	\N	0	0	0.00		2025-06-24 19:48:54.581559-05	0	0	0	0.00	\N
327659	\N	Andrew	Brown	4571	4433	2025-06-24 19:48:54.581559-05	nndz-WkMrNnhMdi9ndz09	4514	t	\N	0	2	0.00		2025-06-24 19:48:54.581559-05	0	0	0	0.00	\N
327660	\N	Andy	Hayman	4571	4433	2025-06-24 19:48:54.581559-05	nndz-WkMrNnhMZjVoQT09	4514	t	\N	0	0	0.00		2025-06-24 19:48:54.581559-05	0	0	0	0.00	\N
327661	\N	Danny	Hest	4571	4433	2025-06-24 19:48:54.581559-05	nndz-WkMrNng3L3doZz09	4514	t	\N	0	0	0.00		2025-06-24 19:48:54.581559-05	0	0	0	0.00	\N
327662	\N	Scott	Lassar	4571	4433	2025-06-24 19:48:54.581559-05	nndz-WkMrNnhMdjRodz09	4514	t	\N	0	0	0.00		2025-06-24 19:48:54.581559-05	0	0	0	0.00	\N
327663	\N	Shai	Lothan	4571	4433	2025-06-24 19:48:54.581559-05	nndz-WkMrNng3NzZnUT09	4514	t	\N	0	0	0.00		2025-06-24 19:48:54.581559-05	0	0	0	0.00	\N
327664	\N	Steve	Reiches	4571	4433	2025-06-24 19:48:54.581559-05	nndz-WlNlNXlMbndnUT09	4514	t	\N	0	0	0.00		2025-06-24 19:48:54.581559-05	0	0	0	0.00	\N
327665	\N	Ari	Sagett	4571	4433	2025-06-24 19:48:54.581559-05	nndz-WlNlNXlMbndnQT09	4514	t	\N	1	0	100.00		2025-06-24 19:48:54.581559-05	0	0	0	0.00	\N
327666	\N	Sandy	Schmidt	4571	4433	2025-06-24 19:48:54.581559-05	nndz-WkMrNng3ejRndz09	4514	t	\N	0	2	0.00		2025-06-24 19:48:54.581559-05	0	0	0	0.00	\N
327667	\N	Howard	Silverman	4571	4433	2025-06-24 19:48:54.581559-05	nndz-WkMrNnhMcjlnUT09	4514	t	\N	0	0	0.00		2025-06-24 19:48:54.581559-05	0	0	0	0.00	\N
327668	\N	Andrew	Strasman	4571	4433	2025-06-24 19:48:54.581559-05	nndz-WkMrNng3Mytodz09	4514	t	\N	0	0	0.00		2025-06-24 19:48:54.581559-05	0	0	0	0.00	\N
327669	\N	Travis	Raebel	4600	4433	2025-06-24 19:48:54.581559-05	nndz-WkMrOHlMejZoZz09	4514	t	\N	1	0	100.00	C	2025-06-24 19:48:54.581559-05	0	0	0	0.00	\N
327670	\N	Kevin	Lewis	4600	4433	2025-06-24 19:48:54.581559-05	nndz-WlNhd3hyaitoZz09	4514	t	\N	1	0	100.00	CC	2025-06-24 19:48:54.581559-05	0	0	0	0.00	\N
327671	\N	Rob	Bentley	4600	4433	2025-06-24 19:48:54.581559-05	nndz-WkMrNng3LzZodz09	4514	t	\N	1	1	50.00		2025-06-24 19:48:54.581559-05	0	0	0	0.00	\N
327672	\N	Corey	Burd	4600	4433	2025-06-24 19:48:54.581559-05	nndz-WkMrNng3endoZz09	4514	t	\N	1	0	100.00		2025-06-24 19:48:54.581559-05	0	0	0	0.00	\N
327673	\N	Mike	Church	4600	4433	2025-06-24 19:48:54.581559-05	nndz-WlNld3hyNy9qUT09	4514	t	\N	0	0	0.00		2025-06-24 19:48:54.581559-05	0	0	0	0.00	\N
327674	\N	Josh	Clifford	4600	4433	2025-06-24 19:48:54.581559-05	nndz-WlNld3hyNy9qQT09	4514	t	\N	0	0	0.00		2025-06-24 19:48:54.581559-05	0	0	0	0.00	\N
327675	\N	Ted	Constantine	4600	4433	2025-06-24 19:48:54.581559-05	nndz-WkMrNnhMYitndz09	4514	t	\N	0	1	0.00		2025-06-24 19:48:54.581559-05	0	0	0	0.00	\N
327676	\N	Jay	Edwards	4600	4433	2025-06-24 19:48:54.581559-05	nndz-WkMrNnhMajVoZz09	4514	t	\N	1	0	100.00		2025-06-24 19:48:54.581559-05	0	0	0	0.00	\N
327677	\N	Ben	Gauthier	4600	4433	2025-06-24 19:48:54.581559-05	nndz-WkMrNnhMYnhoQT09	4514	t	\N	1	1	50.00		2025-06-24 19:48:54.581559-05	0	0	0	0.00	\N
327678	\N	John	Gescheidle	4600	4433	2025-06-24 19:48:54.581559-05	nndz-WkMrOHhidjdndz09	4514	t	\N	0	0	0.00		2025-06-24 19:48:54.581559-05	0	0	0	0.00	\N
327679	\N	Randy	Hara	4600	4433	2025-06-24 19:48:54.581559-05	nndz-WlNhd3hyanhoUT09	4514	t	\N	0	0	0.00		2025-06-24 19:48:54.581559-05	0	0	0	0.00	\N
327680	\N	Gam	Huggins	4600	4433	2025-06-24 19:48:54.581559-05	nndz-WkMrNng3endnUT09	4514	t	\N	0	0	0.00		2025-06-24 19:48:54.581559-05	0	0	0	0.00	\N
327681	\N	Brian	Kelley	4600	4433	2025-06-24 19:48:54.581559-05	nndz-WlNhd3hyanhnUT09	4514	t	\N	0	1	0.00		2025-06-24 19:48:54.581559-05	0	0	0	0.00	\N
327682	\N	Tom	Lesko	4600	4433	2025-06-24 19:48:54.581559-05	nndz-WkMrNnhMYjlqQT09	4514	t	\N	1	0	100.00		2025-06-24 19:48:54.581559-05	0	0	0	0.00	\N
327683	\N	Karl	Lorenz	4600	4433	2025-06-24 19:48:54.581559-05	nndz-WkMrOHhidjdnUT09	4514	t	\N	0	1	0.00		2025-06-24 19:48:54.581559-05	0	0	0	0.00	\N
327684	\N	Pete	Martens	4600	4433	2025-06-24 19:48:54.581559-05	nndz-WkMrNnhMYnhodz09	4514	t	\N	1	0	100.00		2025-06-24 19:48:54.581559-05	0	0	0	0.00	\N
327685	\N	Todd	Ozog	4600	4433	2025-06-24 19:48:54.581559-05	nndz-WkMrOHlMejZnUT09	4514	t	\N	0	0	0.00		2025-06-24 19:48:54.581559-05	0	0	0	0.00	\N
327686	\N	Quentin	Pelser	4600	4433	2025-06-24 19:48:54.581559-05	nndz-WlNhd3hyanhoQT09	4514	t	\N	0	0	0.00		2025-06-24 19:48:54.581559-05	0	0	0	0.00	\N
327687	\N	Jason	Perlioni	4600	4433	2025-06-24 19:48:54.581559-05	nndz-WlNld3hydjlndz09	4514	t	\N	0	0	0.00		2025-06-24 19:48:54.581559-05	0	0	0	0.00	\N
327688	\N	Bruce	Rylance	4600	4433	2025-06-24 19:48:54.581559-05	nndz-WkMrNnhMdjhndz09	4514	t	\N	0	0	0.00		2025-06-24 19:48:54.581559-05	0	0	0	0.00	\N
327689	\N	Marc	Silver	4600	4433	2025-06-24 19:48:54.581559-05	nndz-WkMrNnhMZjlodz09	4514	t	\N	1	0	100.00		2025-06-24 19:48:54.581559-05	0	0	0	0.00	\N
327690	\N	Mike	Tracey	4600	4433	2025-06-24 19:48:54.581559-05	nndz-WlNlNXdiejdnZz09	4514	t	\N	0	0	0.00		2025-06-24 19:48:54.581559-05	0	0	0	0.00	\N
327691	\N	Dan	Wagener	4600	4433	2025-06-24 19:48:54.581559-05	nndz-WlNhd3hyanhoZz09	4514	t	\N	0	0	0.00		2025-06-24 19:48:54.581559-05	0	0	0	0.00	\N
327692	\N	Don	Williams	4600	4433	2025-06-24 19:48:54.581559-05	nndz-WkMrOHhidjdoZz09	4514	t	\N	0	0	0.00		2025-06-24 19:48:54.581559-05	0	0	0	0.00	\N
327693	\N	Christopher	Young	4600	4433	2025-06-24 19:48:54.581559-05	nndz-WkMrNnhMajRodz09	4514	t	\N	1	0	100.00		2025-06-24 19:48:54.581559-05	0	0	0	0.00	\N
327694	\N	Matt	Young	4600	4433	2025-06-24 19:48:54.581559-05	nndz-WlNhd3hyanhodz09	4514	t	\N	1	0	100.00		2025-06-24 19:48:54.581559-05	0	0	0	0.00	\N
327695	\N	michael	sheehan	4616	4433	2025-06-24 19:48:54.581559-05	nndz-WkMrNng3ejZoZz09	4514	t	\N	0	0	0.00	C	2025-06-24 19:48:54.581559-05	0	0	0	0.00	\N
327696	\N	Dave	Fullerton	4616	4433	2025-06-24 19:48:54.581559-05	nndz-WkMrNnhMajhoZz09	4514	t	\N	0	0	0.00	CC	2025-06-24 19:48:54.581559-05	0	0	0	0.00	\N
327697	\N	David	Bailey	4616	4433	2025-06-24 19:48:54.581559-05	nndz-WkMrNng3MzVndz09	4514	t	\N	0	0	0.00		2025-06-24 19:48:54.581559-05	0	0	0	0.00	\N
327698	\N	Ben	Carbonargi	4616	4433	2025-06-24 19:48:54.581559-05	nndz-WkMrNng3MzdnUT09	4514	t	\N	0	0	0.00		2025-06-24 19:48:54.581559-05	0	0	0	0.00	\N
327699	\N	Greg	Hiltebrand	4616	4433	2025-06-24 19:48:54.581559-05	nndz-WkMrNng3MzZoZz09	4514	t	\N	0	0	0.00		2025-06-24 19:48:54.581559-05	0	0	0	0.00	\N
327700	\N	Harris	Jackson	4616	4433	2025-06-24 19:48:54.581559-05	nndz-WkMrNnhMajhnUT09	4514	t	\N	0	0	0.00		2025-06-24 19:48:54.581559-05	0	0	0	0.00	\N
327701	\N	Scott	Jackson	4616	4433	2025-06-24 19:48:54.581559-05	nndz-WkMrNnhMbjVnQT09	4514	t	\N	0	0	0.00		2025-06-24 19:48:54.581559-05	0	0	0	0.00	\N
327702	\N	Dave	Langenbach	4616	4433	2025-06-24 19:48:54.581559-05	nndz-WkMrNnhMMzlnUT09	4514	t	\N	0	0	0.00		2025-06-24 19:48:54.581559-05	0	0	0	0.00	\N
327703	\N	Scott	Lewis	4616	4433	2025-06-24 19:48:54.581559-05	nndz-WkMrNng3MzZoQT09	4514	t	\N	0	0	0.00		2025-06-24 19:48:54.581559-05	0	0	0	0.00	\N
327704	\N	Richard	Messersmith	4616	4433	2025-06-24 19:48:54.581559-05	nndz-WkMrNnhMYjlnZz09	4514	t	\N	0	0	0.00		2025-06-24 19:48:54.581559-05	0	0	0	0.00	\N
327705	\N	Court	5 No Player 1	4616	4433	2025-06-24 19:48:54.581559-05	nndz-WlNlNXdiei9oQT09	4514	t	\N	0	0	0.00		2025-06-24 19:48:54.581559-05	0	0	0	0.00	\N
327706	\N	Tony	Schirmang	4616	4433	2025-06-24 19:48:54.581559-05	nndz-WkMrNng3MzdnZz09	4514	t	\N	0	0	0.00		2025-06-24 19:48:54.581559-05	0	0	0	0.00	\N
327707	\N	Michael	Snabes	4616	4433	2025-06-24 19:48:54.581559-05	nndz-WkMrNnhMbnhndz09	4514	t	\N	0	0	0.00		2025-06-24 19:48:54.581559-05	0	0	0	0.00	\N
327708	\N	Ken	Tuman	4616	4433	2025-06-24 19:48:54.581559-05	nndz-WkMrNnhMcjZodz09	4514	t	\N	0	0	0.00		2025-06-24 19:48:54.581559-05	0	0	0	0.00	\N
327709	\N	Steven	Wolf	4616	4433	2025-06-24 19:48:54.581559-05	nndz-WkMrNng3MzdoQT09	4514	t	\N	0	0	0.00		2025-06-24 19:48:54.581559-05	0	0	0	0.00	\N
327710	\N	Hank	Baby	4616	4433	2025-06-24 19:48:54.581559-05	nndz-WkMrNnhMdjRnUT09	4514	t	\N	0	0	0.00		2025-06-24 19:48:54.581559-05	0	0	0	0.00	\N
327711	\N	Mike	Cavalier	4616	4433	2025-06-24 19:48:54.581559-05	nndz-WkMrNnhMajVnUT09	4514	t	\N	0	0	0.00		2025-06-24 19:48:54.581559-05	0	0	0	0.00	\N
327712	\N	Scott	Frerichs	4616	4433	2025-06-24 19:48:54.581559-05	nndz-WkMrNnhMYitnQT09	4514	t	\N	0	0	0.00		2025-06-24 19:48:54.581559-05	0	0	0	0.00	\N
327713	\N	Mike	Nolan	4616	4433	2025-06-24 19:48:54.581559-05	nndz-WkMrNng3LzdqUT09	4514	t	\N	0	0	0.00		2025-06-24 19:48:54.581559-05	0	0	0	0.00	\N
327714	\N	Dan	Lezotte	4635	4433	2025-06-24 19:48:54.581559-05	nndz-WkMrNnhMcjZnQT09	4514	t	\N	1	0	100.00	C	2025-06-24 19:48:54.581559-05	0	0	0	0.00	\N
327715	\N	Kael	Anderson	4635	4433	2025-06-24 19:48:54.581559-05	nndz-WlNlNXdMNzlqQT09	4514	t	\N	0	0	0.00		2025-06-24 19:48:54.581559-05	0	0	0	0.00	\N
327716	\N	Mark	Anderson	4635	4433	2025-06-24 19:48:54.581559-05	nndz-WkMrOXlMbjZnQT09	4514	t	\N	0	0	0.00		2025-06-24 19:48:54.581559-05	0	0	0	0.00	\N
327717	\N	Tom	Bonnel	4635	4433	2025-06-24 19:48:54.581559-05	nndz-WkMrNnhMMy9ndz09	4514	t	\N	0	0	0.00		2025-06-24 19:48:54.581559-05	0	0	0	0.00	\N
327718	\N	Steve	Bowen	4635	4433	2025-06-24 19:48:54.581559-05	nndz-WkMrOHdiYi9qUT09	4514	t	\N	0	0	0.00		2025-06-24 19:48:54.581559-05	0	0	0	0.00	\N
327719	\N	Robert	Byron	4635	4433	2025-06-24 19:48:54.581559-05	nndz-WkMrOHdycjhoUT09	4514	t	\N	0	0	0.00		2025-06-24 19:48:54.581559-05	0	0	0	0.00	\N
327720	\N	Scott	Corely	4635	4433	2025-06-24 19:48:54.581559-05	nndz-WlNhd3lMMzhoZz09	4514	t	\N	0	0	0.00		2025-06-24 19:48:54.581559-05	0	0	0	0.00	\N
327721	\N	Fritz	Duda	4635	4433	2025-06-24 19:48:54.581559-05	nndz-WkMrNng3Ly9nUT09	4514	t	\N	0	0	0.00		2025-06-24 19:48:54.581559-05	0	0	0	0.00	\N
327722	\N	Peter	Eck	4635	4433	2025-06-24 19:48:54.581559-05	nndz-WkMrOXlMbjZoQT09	4514	t	\N	0	0	0.00		2025-06-24 19:48:54.581559-05	0	0	0	0.00	\N
327723	\N	Karl	Ellensohn	4635	4433	2025-06-24 19:48:54.581559-05	nndz-WkMrNnhMdi9oZz09	4514	t	\N	1	0	100.00		2025-06-24 19:48:54.581559-05	0	0	0	0.00	\N
327724	\N	Erik	Falk	4635	4433	2025-06-24 19:48:54.581559-05	nndz-WlNhd3liNzdoUT09	4514	t	\N	0	0	0.00		2025-06-24 19:48:54.581559-05	0	0	0	0.00	\N
327725	\N	Brian	Fay	4635	4433	2025-06-24 19:48:54.581559-05	nndz-WlNlNXdMai9ndz09	4514	t	\N	0	0	0.00		2025-06-24 19:48:54.581559-05	0	0	0	0.00	\N
327726	\N	Brian	Fay	4635	4433	2025-06-24 19:48:54.581559-05	nndz-WlNlNXdMai9nZz09	4514	t	\N	0	0	0.00		2025-06-24 19:48:54.581559-05	0	0	0	0.00	\N
327727	\N	Mike	Golden	4635	4433	2025-06-24 19:48:54.581559-05	nndz-WkMrOHdycjhodz09	4514	t	\N	1	0	100.00		2025-06-24 19:48:54.581559-05	0	0	0	0.00	\N
327728	\N	Jim	Haft	4635	4433	2025-06-24 19:48:54.581559-05	nndz-WkMrOHdycjhoQT09	4514	t	\N	0	0	0.00		2025-06-24 19:48:54.581559-05	0	0	0	0.00	\N
327729	\N	Davide	Hays	4635	4433	2025-06-24 19:48:54.581559-05	nndz-WkMrOHdiYi9qQT09	4514	t	\N	0	0	0.00		2025-06-24 19:48:54.581559-05	0	0	0	0.00	\N
327730	\N	Chris	Kerns	4635	4433	2025-06-24 19:48:54.581559-05	nndz-WlNhd3liNzRnUT09	4514	t	\N	0	0	0.00		2025-06-24 19:48:54.581559-05	0	0	0	0.00	\N
327731	\N	John	Mathey	4635	4433	2025-06-24 19:48:54.581559-05	nndz-WkMrNng3NzlqUT09	4514	t	\N	0	0	0.00		2025-06-24 19:48:54.581559-05	0	0	0	0.00	\N
327732	\N	Bill	McClain	4635	4433	2025-06-24 19:48:54.581559-05	nndz-WkMrNnhMbjZnZz09	4514	t	\N	0	1	0.00		2025-06-24 19:48:54.581559-05	0	0	0	0.00	\N
327733	\N	Will	McClain	4635	4433	2025-06-24 19:48:54.581559-05	nndz-WkMrNng3MzVqQT09	4514	t	\N	0	0	0.00		2025-06-24 19:48:54.581559-05	0	0	0	0.00	\N
327734	\N	Rich	McMenamin	4635	4433	2025-06-24 19:48:54.581559-05	nndz-WkMrNnhMdjVqQT09	4514	t	\N	0	0	0.00		2025-06-24 19:48:54.581559-05	0	0	0	0.00	\N
327735	\N	Michael	OBrien	4635	4433	2025-06-24 19:48:54.581559-05	nndz-WkMrNnhMbndqUT09	4514	t	\N	2	0	100.00		2025-06-24 19:48:54.581559-05	0	0	0	0.00	\N
327736	\N	Mike	Paleczny	4635	4433	2025-06-24 19:48:54.581559-05	nndz-WlNlNXhyYjdodz09	4514	t	\N	0	1	0.00		2025-06-24 19:48:54.581559-05	0	0	0	0.00	\N
327737	\N	Bob	Petrie	4635	4433	2025-06-24 19:48:54.581559-05	nndz-WlNhd3liNzRodz09	4514	t	\N	0	0	0.00		2025-06-24 19:48:54.581559-05	0	0	0	0.00	\N
327738	\N	Jim	Pigott Pigott	4635	4433	2025-06-24 19:48:54.581559-05	nndz-WkMrOXlMbjdnZz09	4514	t	\N	0	0	0.00		2025-06-24 19:48:54.581559-05	0	0	0	0.00	\N
327739	\N	Jeff	Ramsay	4635	4433	2025-06-24 19:48:54.581559-05	nndz-WkMrNnhMdjRoUT09	4514	t	\N	0	0	0.00		2025-06-24 19:48:54.581559-05	0	0	0	0.00	\N
327740	\N	Robert	Rudy	4635	4433	2025-06-24 19:48:54.581559-05	nndz-WkMrNnhMMzdnQT09	4514	t	\N	0	0	0.00		2025-06-24 19:48:54.581559-05	0	0	0	0.00	\N
327741	\N	Richard	Sanderson	4635	4433	2025-06-24 19:48:54.581559-05	nndz-WkMrOHdycjhoZz09	4514	t	\N	1	0	100.00		2025-06-24 19:48:54.581559-05	0	0	0	0.00	\N
327742	\N	Scott	Schoder	4635	4433	2025-06-24 19:48:54.581559-05	nndz-WlNhd3liNzRoQT09	4514	t	\N	0	0	0.00		2025-06-24 19:48:54.581559-05	0	0	0	0.00	\N
327743	\N	Gary	Shapiro	4635	4433	2025-06-24 19:48:54.581559-05	nndz-WlNlNHhiLzRqQT09	4514	t	\N	0	0	0.00		2025-06-24 19:48:54.581559-05	0	0	0	0.00	\N
327744	\N	Jeff	Shaw	4635	4433	2025-06-24 19:48:54.581559-05	nndz-WlNlNXdiMzVoUT09	4514	t	\N	1	0	100.00		2025-06-24 19:48:54.581559-05	0	0	0	0.00	\N
327745	\N	1	court 5 player Skokie	4635	4433	2025-06-24 19:48:54.581559-05	nndz-WlNhd3lMMzhqQT09	4514	t	\N	1	0	100.00		2025-06-24 19:48:54.581559-05	0	0	0	0.00	\N
327746	\N	2	court 5 player Skokie	4635	4433	2025-06-24 19:48:54.581559-05	nndz-WlNhd3lMMy9oUT09	4514	t	\N	1	0	100.00		2025-06-24 19:48:54.581559-05	0	0	0	0.00	\N
327747	\N	Barrett	Stephan	4635	4433	2025-06-24 19:48:54.581559-05	nndz-WkMrOXlMbjdndz09	4514	t	\N	0	0	0.00		2025-06-24 19:48:54.581559-05	0	0	0	0.00	\N
327748	\N	Max	Weigandt	4635	4433	2025-06-24 19:48:54.581559-05	nndz-WlNlNHc3djZnZz09	4514	t	\N	0	0	0.00		2025-06-24 19:48:54.581559-05	0	0	0	0.00	\N
327749	\N	Peter	Wilson	4635	4433	2025-06-24 19:48:54.581559-05	nndz-WkMrOXlMbjZodz09	4514	t	\N	0	0	0.00		2025-06-24 19:48:54.581559-05	0	0	0	0.00	\N
327750	\N	Roger	Yapp	4635	4433	2025-06-24 19:48:54.581559-05	nndz-WlNlNHdycjRodz09	4514	t	\N	0	0	0.00		2025-06-24 19:48:54.581559-05	0	0	0	0.00	\N
327751	\N	Gordon	Gluckman	4635	4433	2025-06-24 19:48:54.581559-05	nndz-WkMrNnhMdjloUT09	4514	t	\N	0	0	0.00		2025-06-24 19:48:54.581559-05	0	0	0	0.00	\N
327752	\N	Michael	Razzoog	4638	4433	2025-06-24 19:48:54.581559-05	nndz-WlNld3liditnQT09	4514	t	\N	0	0	0.00	C	2025-06-24 19:48:54.581559-05	0	0	0	0.00	\N
327753	\N	Jeremy	Baker	4638	4433	2025-06-24 19:48:54.581559-05	nndz-WkMrOXliejhodz09	4514	t	\N	0	1	0.00		2025-06-24 19:48:54.581559-05	0	0	0	0.00	\N
327754	\N	Josh	Black	4638	4433	2025-06-24 19:48:54.581559-05	nndz-WlNld3lMMzZqUT09	4514	t	\N	0	0	0.00		2025-06-24 19:48:54.581559-05	0	0	0	0.00	\N
327755	\N	Howard	Dakoff	4638	4433	2025-06-24 19:48:54.581559-05	nndz-WkMrOXliejhnQT09	4514	t	\N	0	0	0.00		2025-06-24 19:48:54.581559-05	0	0	0	0.00	\N
327756	\N	Nelson	Gomez	4638	4433	2025-06-24 19:48:54.581559-05	nndz-WkMrNng3ejZqUT09	4514	t	\N	0	0	0.00		2025-06-24 19:48:54.581559-05	0	0	0	0.00	\N
327757	\N	Ryan	Jarol	4638	4433	2025-06-24 19:48:54.581559-05	nndz-WkMrOXliei9oQT09	4514	t	\N	0	0	0.00		2025-06-24 19:48:54.581559-05	0	0	0	0.00	\N
327758	\N	Jeffery	Kivetz	4638	4433	2025-06-24 19:48:54.581559-05	nndz-WlNld3libitodz09	4514	t	\N	0	1	0.00		2025-06-24 19:48:54.581559-05	0	0	0	0.00	\N
327759	\N	Bryan	Komornik	4638	4433	2025-06-24 19:48:54.581559-05	nndz-WlNld3lMMzZnZz09	4514	t	\N	0	0	0.00		2025-06-24 19:48:54.581559-05	0	0	0	0.00	\N
327760	\N	Jason	Kray	4638	4433	2025-06-24 19:48:54.581559-05	nndz-WlNld3libitoZz09	4514	t	\N	0	1	0.00		2025-06-24 19:48:54.581559-05	0	0	0	0.00	\N
327761	\N	Wes	Maher	4638	4433	2025-06-24 19:48:54.581559-05	nndz-WlNld3libitnUT09	4514	t	\N	0	1	0.00		2025-06-24 19:48:54.581559-05	0	0	0	0.00	\N
327762	\N	Greg	Meagher	4638	4433	2025-06-24 19:48:54.581559-05	nndz-WkMrNng3ejlnUT09	4514	t	\N	0	1	0.00		2025-06-24 19:48:54.581559-05	0	0	0	0.00	\N
327763	\N	David	Ransburg	4638	4433	2025-06-24 19:48:54.581559-05	nndz-WkMrOXlibjZnZz09	4514	t	\N	0	0	0.00		2025-06-24 19:48:54.581559-05	0	0	0	0.00	\N
327764	\N	Dave	Rogers	4638	4433	2025-06-24 19:48:54.581559-05	nndz-WlNld3libitnQT09	4514	t	\N	0	0	0.00		2025-06-24 19:48:54.581559-05	0	0	0	0.00	\N
327765	\N	Marc	Sher	4638	4433	2025-06-24 19:48:54.581559-05	nndz-WlNld3libitndz09	4514	t	\N	0	0	0.00		2025-06-24 19:48:54.581559-05	0	0	0	0.00	\N
327766	\N	Joe	Fink	4638	4433	2025-06-24 19:48:54.581559-05	nndz-WlNTNXdyYjlqUT09	4514	t	\N	0	0	0.00		2025-06-24 19:48:54.581559-05	0	0	0	0.00	\N
327767	\N	Nick	Gomez	4638	4433	2025-06-24 19:48:54.581559-05	nndz-WlNTNXdyYjhodz09	4514	t	\N	0	0	0.00		2025-06-24 19:48:54.581559-05	0	0	0	0.00	\N
327768	\N	Kurt	Kleckner	4638	4433	2025-06-24 19:48:54.581559-05	nndz-WlNld3lMMzloQT09	4514	t	\N	0	0	0.00		2025-06-24 19:48:54.581559-05	0	0	0	0.00	\N
327769	\N	Jordan	Mackay	4638	4433	2025-06-24 19:48:54.581559-05	nndz-WlNTNXdyYjlqQT09	4514	t	\N	0	0	0.00		2025-06-24 19:48:54.581559-05	0	0	0	0.00	\N
327770	\N	Mariano	Martinez	4638	4433	2025-06-24 19:48:54.581559-05	nndz-WlNhd3hMYi9nZz09	4514	t	\N	0	1	0.00		2025-06-24 19:48:54.581559-05	0	0	0	0.00	\N
327771	\N	Ryan	McNamara	4638	4433	2025-06-24 19:48:54.581559-05	nndz-WlNTNXdyYjlnZz09	4514	t	\N	1	0	100.00		2025-06-24 19:48:54.581559-05	0	0	0	0.00	\N
327772	\N	Alex	Pike	4638	4433	2025-06-24 19:48:54.581559-05	nndz-WlNTNXdyYjhnQT09	4514	t	\N	1	0	100.00		2025-06-24 19:48:54.581559-05	0	0	0	0.00	\N
327773	\N	Blake	Schulman	4638	4433	2025-06-24 19:48:54.581559-05	nndz-WlNTNXdyYjhoZz09	4514	t	\N	0	0	0.00		2025-06-24 19:48:54.581559-05	0	0	0	0.00	\N
327774	\N	Michael	Spector	4638	4433	2025-06-24 19:48:54.581559-05	nndz-WlNTNXdyYjhoQT09	4514	t	\N	0	0	0.00		2025-06-24 19:48:54.581559-05	0	0	0	0.00	\N
327775	\N	Ryan	Andrews	4639	4433	2025-06-24 19:48:54.581559-05	nndz-WkMrNnhMYjRoQT09	4514	t	\N	1	0	100.00		2025-06-24 19:48:54.581559-05	0	0	0	0.00	\N
327776	\N	Patrick	Baele	4639	4433	2025-06-24 19:48:54.581559-05	nndz-WkMrNnhMZjRoQT09	4514	t	\N	1	0	100.00		2025-06-24 19:48:54.581559-05	0	0	0	0.00	\N
327777	\N	Paul	Bianco	4639	4433	2025-06-24 19:48:54.581559-05	nndz-WkMrNng3ejZndz09	4514	t	\N	1	0	100.00		2025-06-24 19:48:54.581559-05	0	0	0	0.00	\N
327778	\N	Evan	Clark	4639	4433	2025-06-24 19:48:54.581559-05	nndz-WkMrNng3My9ndz09	4514	t	\N	0	0	0.00		2025-06-24 19:48:54.581559-05	0	0	0	0.00	\N
327779	\N	Mario	Divito	4639	4433	2025-06-24 19:48:54.581559-05	nndz-WkMrNnhMYjdnUT09	4514	t	\N	0	0	0.00		2025-06-24 19:48:54.581559-05	0	0	0	0.00	\N
327780	\N	Joe	Doucas	4639	4433	2025-06-24 19:48:54.581559-05	nndz-WkMrNnhMZnhqQT09	4514	t	\N	0	0	0.00		2025-06-24 19:48:54.581559-05	0	0	0	0.00	\N
327781	\N	Steven	Fass	4639	4433	2025-06-24 19:48:54.581559-05	nndz-WkMrNnhMYjdqQT09	4514	t	\N	0	0	0.00		2025-06-24 19:48:54.581559-05	0	0	0	0.00	\N
327782	\N	Kris	Langager	4639	4433	2025-06-24 19:48:54.581559-05	nndz-WkMrNng3ejlqUT09	4514	t	\N	0	0	0.00		2025-06-24 19:48:54.581559-05	0	0	0	0.00	\N
327783	\N	Chris	Leisz	4639	4433	2025-06-24 19:48:54.581559-05	nndz-WkMrNng3LzVoQT09	4514	t	\N	0	0	0.00		2025-06-24 19:48:54.581559-05	0	0	0	0.00	\N
327784	\N	Ivan	Martinez Fernandez	4639	4433	2025-06-24 19:48:54.581559-05	nndz-WkMrNng3NzhoQT09	4514	t	\N	0	0	0.00		2025-06-24 19:48:54.581559-05	0	0	0	0.00	\N
327785	\N	Brad	Nagel	4639	4433	2025-06-24 19:48:54.581559-05	nndz-WkMrNng3ejVoQT09	4514	t	\N	1	0	100.00		2025-06-24 19:48:54.581559-05	0	0	0	0.00	\N
327786	\N	Jim	O'Shaughnessy	4639	4433	2025-06-24 19:48:54.581559-05	nndz-WkMrNng3LzVoUT09	4514	t	\N	0	0	0.00		2025-06-24 19:48:54.581559-05	0	0	0	0.00	\N
327787	\N	Jay	Poydence	4639	4433	2025-06-24 19:48:54.581559-05	nndz-WkMrNnhMZjRodz09	4514	t	\N	0	0	0.00		2025-06-24 19:48:54.581559-05	0	0	0	0.00	\N
327788	\N	Mark	Cunnington	4581	4260	2025-06-24 19:48:54.581559-05	nndz-WkNPd3hMei9oQT09	4511	t	14.50	5	7	41.70	C	2025-06-24 19:48:54.581559-05	0	0	0	0.00	13457
327789	\N	Reece	Acree	4581	4260	2025-06-24 19:48:54.581559-05	nndz-WlNlN3lMZjhnZz09	4511	t	\N	1	2	33.30		2025-06-24 19:48:54.581559-05	0	0	0	0.00	13457
327790	\N	Ryan	Edlefsen	4581	4260	2025-06-24 19:48:54.581559-05	nndz-WkNPd3hMcnhoQT09	4511	t	\N	11	4	73.30		2025-06-24 19:48:54.581559-05	0	0	0	0.00	13457
327791	\N	Mitch	Granger	4581	4260	2025-06-24 19:48:54.581559-05	nndz-WkNPd3hMMzRoQT09	4511	t	\N	12	5	70.60		2025-06-24 19:48:54.581559-05	0	0	0	0.00	13457
327792	\N	Radek	Guzik	4581	4260	2025-06-24 19:48:54.581559-05	nndz-WkNPd3hMejhndz09	4511	t	14.80	11	15	42.30		2025-06-24 19:48:54.581559-05	0	0	0	0.00	13457
327793	\N	Anthony	McPherson	4581	4260	2025-06-24 19:48:54.581559-05	nndz-WkNPd3hMei9qUT09	4511	t	\N	19	10	65.50		2025-06-24 19:48:54.581559-05	0	0	0	0.00	13457
327794	\N	Eric	Pohl	4581	4260	2025-06-24 19:48:54.581559-05	nndz-WkNDOXhyLytoZz09	4511	t	\N	23	10	69.70		2025-06-24 19:48:54.581559-05	0	0	0	0.00	13457
327795	\N	Scott	Rutherford	4581	4260	2025-06-24 19:48:54.581559-05	nndz-WkNDd3lMLzlqQT09	4511	t	\N	7	2	77.80		2025-06-24 19:48:54.581559-05	0	0	0	0.00	13457
327796	\N	Adam	Schumacher	4581	4260	2025-06-24 19:48:54.581559-05	nndz-WkNPd3g3ejhnUT09	4511	t	\N	10	5	66.70		2025-06-24 19:48:54.581559-05	0	0	0	0.00	13457
327797	\N	Trey	Scott	4581	4260	2025-06-24 19:48:54.581559-05	nndz-WkNDNnlMai9oZz09	4511	t	\N	6	4	60.00		2025-06-24 19:48:54.581559-05	0	0	0	0.00	13457
327798	\N	Krishin	Shivdasani	4581	4260	2025-06-24 19:48:54.581559-05	nndz-WkNDOXdidjhqQT09	4511	t	15.60	6	9	40.00		2025-06-24 19:48:54.581559-05	0	0	0	0.00	13457
327799	\N	Jason	Stanislaw	4581	4260	2025-06-24 19:48:54.581559-05	nndz-WkNPd3hMcndodz09	4511	t	24.20	7	16	30.40		2025-06-24 19:48:54.581559-05	0	0	0	0.00	13457
327800	\N	Peter	Rose	4585	4260	2025-06-24 19:48:54.581559-05	nndz-WkNPd3hMendqQT09	4511	t	\N	7	7	50.00	C	2025-06-24 19:48:54.581559-05	0	0	0	0.00	13479
327801	\N	Andrew	Buchholz	4585	4260	2025-06-24 19:48:54.581559-05	nndz-WkNPd3hMditoZz09	4511	t	\N	10	8	55.60		2025-06-24 19:48:54.581559-05	0	0	0	0.00	13479
327802	\N	Nick	Cromydas	4585	4260	2025-06-24 19:48:54.581559-05	nndz-WkNPd3hMendnQT09	4511	t	\N	7	5	58.30		2025-06-24 19:48:54.581559-05	0	0	0	0.00	13479
327803	\N	Scott	Green	4585	4260	2025-06-24 19:48:54.581559-05	nndz-WkNPd3hMMzZnZz09	4511	t	\N	16	14	53.30		2025-06-24 19:48:54.581559-05	0	0	0	0.00	13479
327804	\N	Ben	McKnight	4585	4260	2025-06-24 19:48:54.581559-05	nndz-WkNPd3hMMzVodz09	4511	t	\N	9	8	52.90		2025-06-24 19:48:54.581559-05	0	0	0	0.00	13479
327805	\N	Mike	Rahaley	4585	4260	2025-06-24 19:48:54.581559-05	nndz-WkNPd3hMeitnQT09	4511	t	\N	0	0	0.00		2025-06-24 19:48:54.581559-05	0	0	0	0.00	13479
327806	\N	Paul	Rose	4585	4260	2025-06-24 19:48:54.581559-05	nndz-WkNPd3hMendnUT09	4511	t	\N	8	9	47.10		2025-06-24 19:48:54.581559-05	0	0	0	0.00	13479
327807	\N	Harry	Sullivan	4585	4260	2025-06-24 19:48:54.581559-05	nndz-WkNPd3hMMzRqUT09	4511	t	\N	19	5	79.20		2025-06-24 19:48:54.581559-05	0	0	0	0.00	13479
327808	\N	Matthew	Warner	4585	4260	2025-06-24 19:48:54.581559-05	nndz-WkNPd3hMejhnZz09	4511	t	\N	13	9	59.10		2025-06-24 19:48:54.581559-05	0	0	0	0.00	13479
327809	\N	Jay	Woldenberg	4586	4260	2025-06-24 19:48:54.581559-05	nndz-WkNPd3hMendnZz09	4511	t	\N	7	13	35.00	C	2025-06-24 19:48:54.581559-05	0	0	0	0.00	13491
327810	\N	Peter	Berka	4586	4260	2025-06-24 19:48:54.581559-05	nndz-WkNPd3hMMzVqQT09	4511	t	\N	21	8	72.40		2025-06-24 19:48:54.581559-05	0	0	0	0.00	13491
327811	\N	Bryan	Bertola	4586	4260	2025-06-24 19:48:54.581559-05	nndz-WkM2OHg3citqQT09	4511	t	16.20	16	19	45.70		2025-06-24 19:48:54.581559-05	0	0	0	0.00	13491
327812	\N	Scott	Bondurant	4586	4260	2025-06-24 19:48:54.581559-05	nndz-WkNPd3hMMzdndz09	4511	t	\N	7	9	43.80		2025-06-24 19:48:54.581559-05	0	0	0	0.00	13491
327813	\N	Stu	Bradley	4586	4260	2025-06-24 19:48:54.581559-05	nndz-WkNPd3hMMytnQT09	4511	t	\N	7	6	53.80		2025-06-24 19:48:54.581559-05	0	0	0	0.00	13491
327814	\N	Kenny	Burst	4586	4260	2025-06-24 19:48:54.581559-05	nndz-WkMrN3g3LzVoQT09	4511	t	\N	2	0	100.00		2025-06-24 19:48:54.581559-05	0	0	0	0.00	13491
327815	\N	Alex	Cotard	4586	4260	2025-06-24 19:48:54.581559-05	nndz-WkM2L3dMbi9oZz09	4511	t	\N	13	8	61.90		2025-06-24 19:48:54.581559-05	0	0	0	0.00	13491
327816	\N	Christian	Duchnak	4586	4260	2025-06-24 19:48:54.581559-05	nndz-WkM2K3c3cnhoUT09	4511	t	\N	18	4	81.80		2025-06-24 19:48:54.581559-05	0	0	0	0.00	13491
327817	\N	Brian	Faig	4586	4260	2025-06-24 19:48:54.581559-05	nndz-WkNHeHg3ditoQT09	4511	t	\N	15	11	57.70		2025-06-24 19:48:54.581559-05	0	0	0	0.00	13491
327818	\N	Dave	Fritzsche	4586	4260	2025-06-24 19:48:54.581559-05	nndz-WkNPd3hMMzdodz09	4511	t	\N	16	14	53.30		2025-06-24 19:48:54.581559-05	0	0	0	0.00	13491
327819	\N	Daniel	Levine	4586	4260	2025-06-24 19:48:54.581559-05	nndz-WkNHeHc3bnhqUT09	4511	t	\N	12	16	42.90		2025-06-24 19:48:54.581559-05	0	0	0	0.00	13491
327820	\N	Jeff	Martin	4586	4260	2025-06-24 19:48:54.581559-05	nndz-WkNPd3hMMzZqUT09	4511	t	13.10	3	5	37.50		2025-06-24 19:48:54.581559-05	0	0	0	0.00	13491
327821	\N	Jonas	Merckx	4586	4260	2025-06-24 19:48:54.581559-05	nndz-WkM2L3g3andnZz09	4511	t	\N	30	3	90.90		2025-06-24 19:48:54.581559-05	0	0	0	0.00	13491
327822	\N	Andrew	Ong	4586	4260	2025-06-24 19:48:54.581559-05	nndz-WkM2L3hMLzdqQT09	4511	t	\N	16	3	84.20		2025-06-24 19:48:54.581559-05	0	0	0	0.00	13491
327823	\N	John	Silk	4586	4260	2025-06-24 19:48:54.581559-05	nndz-WkNPd3hMMzdoUT09	4511	t	\N	8	9	47.10		2025-06-24 19:48:54.581559-05	0	0	0	0.00	13491
327824	\N	Sean	Weber	4586	4260	2025-06-24 19:48:54.581559-05	nndz-WlNhL3dycjRqQT09	4511	t	\N	10	5	66.70		2025-06-24 19:48:54.581559-05	0	0	0	0.00	13491
327825	\N	Stephen	Larko	4604	4260	2025-06-24 19:48:54.581559-05	nndz-WkNPd3hMYjZqQT09	4511	t	12.40	20	19	51.30	C	2025-06-24 19:48:54.581559-05	0	0	0	0.00	13652
327826	\N	Brett	Binkley	4604	4260	2025-06-24 19:48:54.581559-05	nndz-WkNHeHhMN3dnZz09	4511	t	\N	7	8	46.70		2025-06-24 19:48:54.581559-05	0	0	0	0.00	13652
327827	\N	Anthony	Appleyard	4604	4260	2025-06-24 19:48:54.581559-05	nndz-WkNDd3lMajdodz09	4511	t	\N	18	17	51.40		2025-06-24 19:48:54.581559-05	0	0	0	0.00	13652
327828	\N	Ben	Ashford	4604	4260	2025-06-24 19:48:54.581559-05	nndz-WkNPd3hMMzZoUT09	4511	t	\N	5	6	45.50		2025-06-24 19:48:54.581559-05	0	0	0	0.00	13652
327829	\N	Jeronie	Barnes	4604	4260	2025-06-24 19:48:54.581559-05	nndz-WkNPd3hMendoUT09	4511	t	\N	8	4	66.70		2025-06-24 19:48:54.581559-05	0	0	0	0.00	13652
327830	\N	Jonathan`	Cantwell	4604	4260	2025-06-24 19:48:54.581559-05	nndz-WkNHeHhiejlnZz09	4511	t	15.70	0	0	0.00		2025-06-24 19:48:54.581559-05	0	0	0	0.00	13652
327831	\N	Marek	Czerwinski	4604	4260	2025-06-24 19:48:54.581559-05	nndz-WkNPd3hMeitnUT09	4511	t	\N	9	3	75.00		2025-06-24 19:48:54.581559-05	0	0	0	0.00	13652
327832	\N	Derek	Fish	4604	4260	2025-06-24 19:48:54.581559-05	nndz-WkNPd3hMbi9ndz09	4511	t	18.30	7	12	36.80		2025-06-24 19:48:54.581559-05	0	0	0	0.00	13652
327833	\N	Brandon	Fisher	4604	4260	2025-06-24 19:48:54.581559-05	nndz-WkM2L3hMcjZnQT09	4511	t	\N	11	15	42.30		2025-06-24 19:48:54.581559-05	0	0	0	0.00	13652
327834	\N	Michael	Franco	4604	4260	2025-06-24 19:48:54.581559-05	nndz-WkNPd3hMcjZoZz09	4511	t	\N	16	20	44.40		2025-06-24 19:48:54.581559-05	0	0	0	0.00	13652
327835	\N	Jacob	Groce	4604	4260	2025-06-24 19:48:54.581559-05	nndz-WkMreHdiN3doUT09	4511	t	13.80	11	19	36.70		2025-06-24 19:48:54.581559-05	0	0	0	0.00	13652
327836	\N	Peter	Hammond	4604	4260	2025-06-24 19:48:54.581559-05	nndz-WkNPd3hMajVodz09	4511	t	11.40	10	8	55.60		2025-06-24 19:48:54.581559-05	0	0	0	0.00	13652
327837	\N	Charlie	Howard	4604	4260	2025-06-24 19:48:54.581559-05	nndz-WkNPd3hMM3dnUT09	4511	t	\N	11	15	42.30		2025-06-24 19:48:54.581559-05	0	0	0	0.00	13652
327838	\N	Alex	Lambropoulos	4604	4260	2025-06-24 19:48:54.581559-05	nndz-WkNPd3hMei9nQT09	4511	t	\N	8	5	61.50		2025-06-24 19:48:54.581559-05	0	0	0	0.00	13652
327839	\N	Sam	Meyer	4604	4260	2025-06-24 19:48:54.581559-05	nndz-WkNHeHc3Yi9oZz09	4511	t	19.00	11	12	47.80		2025-06-24 19:48:54.581559-05	0	0	0	0.00	13652
327840	\N	David	Pollack	4604	4260	2025-06-24 19:48:54.581559-05	nndz-WkNHeHhMbjZoZz09	4511	t	13.90	1	2	33.30		2025-06-24 19:48:54.581559-05	0	0	0	0.00	13652
327841	\N	Bradford	Smith	4604	4260	2025-06-24 19:48:54.581559-05	nndz-WkNHL3hiLzRndz09	4511	t	\N	15	5	75.00		2025-06-24 19:48:54.581559-05	0	0	0	0.00	13652
327842	\N	James	Franke	4643	4260	2025-06-24 19:48:54.581559-05	nndz-WkNPd3hMcjdoQT09	4511	t	11.20	6	9	40.00	C	2025-06-24 19:48:54.581559-05	0	0	0	0.00	14030
327843	\N	Steve	Baby	4643	4260	2025-06-24 19:48:54.581559-05	nndz-WkNPd3hMMytnUT09	4511	t	\N	8	7	53.30	CC	2025-06-24 19:48:54.581559-05	0	0	0	0.00	14030
327844	\N	Drew	Campbell	4643	4260	2025-06-24 19:48:54.581559-05	nndz-WkNPd3hMdjRoUT09	4511	t	\N	4	5	44.40		2025-06-24 19:48:54.581559-05	0	0	0	0.00	14030
327845	\N	Jake	Jenner	4643	4260	2025-06-24 19:48:54.581559-05	nndz-WkNPd3hMcjRnQT09	4511	t	11.60	0	0	0.00		2025-06-24 19:48:54.581559-05	0	0	0	0.00	14030
327846	\N	Eric	Koppmann	4643	4260	2025-06-24 19:48:54.581559-05	nndz-WkNHN3dyZnhoUT09	4511	t	16.30	5	14	26.30		2025-06-24 19:48:54.581559-05	0	0	0	0.00	14030
327847	\N	Josh	Kritzler	4643	4260	2025-06-24 19:48:54.581559-05	nndz-WkNPd3hMMzdqQT09	4511	t	\N	8	12	40.00		2025-06-24 19:48:54.581559-05	0	0	0	0.00	14030
327848	\N	Graham	McNerney	4643	4260	2025-06-24 19:48:54.581559-05	nndz-WkNPd3hMMzlnQT09	4511	t	\N	6	3	66.70		2025-06-24 19:48:54.581559-05	0	0	0	0.00	14030
327849	\N	Trey	Minter	4643	4260	2025-06-24 19:48:54.581559-05	nndz-WkNPd3hMcjRnUT09	4511	t	10.00	14	10	58.30		2025-06-24 19:48:54.581559-05	0	0	0	0.00	14030
327850	\N	Paget	Neave	4643	4260	2025-06-24 19:48:54.581559-05	nndz-WkNPd3hMMzlnZz09	4511	t	\N	17	16	51.50		2025-06-24 19:48:54.581559-05	0	0	0	0.00	14030
327851	\N	Mackey	Pierce	4643	4260	2025-06-24 19:48:54.581559-05	nndz-WkNPd3hMei9nUT09	4511	t	\N	19	16	54.30		2025-06-24 19:48:54.581559-05	0	0	0	0.00	14030
327852	\N	Jeff	Rightnour	4643	4260	2025-06-24 19:48:54.581559-05	nndz-WkMrK3hiNzZoUT09	4511	t	\N	9	10	47.40		2025-06-24 19:48:54.581559-05	0	0	0	0.00	14030
327853	\N	Tom	Rowland	4643	4260	2025-06-24 19:48:54.581559-05	nndz-WkNPd3hMMzVoUT09	4511	t	\N	12	9	57.10		2025-06-24 19:48:54.581559-05	0	0	0	0.00	14030
327854	\N	Jeremy	Shull	4643	4260	2025-06-24 19:48:54.581559-05	nndz-WkNPd3hMM3hnUT09	4511	t	12.30	10	6	62.50		2025-06-24 19:48:54.581559-05	0	0	0	0.00	14030
327855	\N	Robert	Stineman	4643	4260	2025-06-24 19:48:54.581559-05	nndz-WkNPd3hMMzRnQT09	4511	t	\N	13	5	72.20		2025-06-24 19:48:54.581559-05	0	0	0	0.00	14030
327856	\N	Connor	Casas	4646	4260	2025-06-24 19:48:54.581559-05	nndz-WkNDNnhyYjZoQT09	4511	t	15.60	15	7	68.20	C	2025-06-24 19:48:54.581559-05	0	0	0	0.00	14067
327857	\N	David	Bukowski	4646	4260	2025-06-24 19:48:54.581559-05	nndz-WkNPd3hMendoZz09	4511	t	\N	12	7	63.20		2025-06-24 19:48:54.581559-05	0	0	0	0.00	14067
327858	\N	Sasha	Djordjevic	4646	4260	2025-06-24 19:48:54.581559-05	nndz-WkNPd3hMMzVnUT09	4511	t	\N	7	8	46.70		2025-06-24 19:48:54.581559-05	0	0	0	0.00	14067
327859	\N	Scott	Hill	4646	4260	2025-06-24 19:48:54.581559-05	nndz-WkNPd3hMdjRqQT09	4511	t	\N	20	10	66.70		2025-06-24 19:48:54.581559-05	0	0	0	0.00	14067
327860	\N	Gabe	Korach	4646	4260	2025-06-24 19:48:54.581559-05	nndz-WkNPd3hManhnZz09	4511	t	\N	14	3	82.40		2025-06-24 19:48:54.581559-05	0	0	0	0.00	14067
327861	\N	Tom	Moore	4646	4260	2025-06-24 19:48:54.581559-05	nndz-WkNPd3hMMzZndz09	4511	t	\N	12	13	48.00		2025-06-24 19:48:54.581559-05	0	0	0	0.00	14067
327862	\N	Danny	Oaks	4646	4260	2025-06-24 19:48:54.581559-05	nndz-WkNDNnlMaitndz09	4511	t	\N	13	15	46.40		2025-06-24 19:48:54.581559-05	0	0	0	0.00	14067
327863	\N	Brian	Panek	4646	4260	2025-06-24 19:48:54.581559-05	nndz-WkNPd3hMenhqUT09	4511	t	\N	17	7	70.80		2025-06-24 19:48:54.581559-05	0	0	0	0.00	14067
327864	\N	Mick	Parks	4646	4260	2025-06-24 19:48:54.581559-05	nndz-WkNPd3hMcjZqQT09	4511	t	\N	13	13	50.00		2025-06-24 19:48:54.581559-05	0	0	0	0.00	14067
327865	\N	Dan	Rosenberg	4646	4260	2025-06-24 19:48:54.581559-05	nndz-WkNPd3g3NzRnZz09	4511	t	\N	9	15	37.50		2025-06-24 19:48:54.581559-05	0	0	0	0.00	14067
327866	\N	Vukasin	Teofanovic	4646	4260	2025-06-24 19:48:54.581559-05	nndz-WkNHeHhiejlnQT09	4511	t	\N	2	8	20.00		2025-06-24 19:48:54.581559-05	0	0	0	0.00	14067
327867	\N	Eddie	Trapp	4646	4260	2025-06-24 19:48:54.581559-05	nndz-WkNHNXdiajhoQT09	4511	t	\N	18	14	56.20		2025-06-24 19:48:54.581559-05	0	0	0	0.00	14067
327868	\N	Greg	Wotring	4646	4260	2025-06-24 19:48:54.581559-05	nndz-WkNPd3hMMzVnQT09	4511	t	\N	16	9	64.00		2025-06-24 19:48:54.581559-05	0	0	0	0.00	14067
327869	\N	Gabe	Korach	4571	4276	2025-06-24 19:48:54.581559-05	nndz-WkNPd3hManhnZz09	4511	t	\N	14	3	82.40	C	2025-06-24 19:48:54.581559-05	0	0	0	0.00	13352
327870	\N	Ricky	Bortz	4571	4276	2025-06-24 19:48:54.581559-05	nndz-WkNDd3lMdjZqQT09	4511	t	19.40	2	9	18.20		2025-06-24 19:48:54.581559-05	0	0	0	0.00	13352
327871	\N	Will	Colmar	4571	4276	2025-06-24 19:48:54.581559-05	nndz-WkNPd3hMeitoZz09	4511	t	\N	14	6	70.00		2025-06-24 19:48:54.581559-05	0	0	0	0.00	13352
327872	\N	Rob	Fenton	4571	4276	2025-06-24 19:48:54.581559-05	nndz-WkNPd3hMandoZz09	4511	t	15.30	7	8	46.70		2025-06-24 19:48:54.581559-05	0	0	0	0.00	13352
327873	\N	Brandon	Fisher	4571	4276	2025-06-24 19:48:54.581559-05	nndz-WkM2L3hMcjZnQT09	4511	t	\N	11	15	42.30		2025-06-24 19:48:54.581559-05	0	0	0	0.00	13352
327874	\N	Adam	Gooze	4571	4276	2025-06-24 19:48:54.581559-05	nndz-WkNDOXhMLzRnQT09	4511	t	23.50	4	12	25.00		2025-06-24 19:48:54.581559-05	0	0	0	0.00	13352
327875	\N	Marv	Gurevich	4571	4276	2025-06-24 19:48:54.581559-05	nndz-WkNDd3lMdjlodz09	4511	t	22.10	3	12	20.00		2025-06-24 19:48:54.581559-05	0	0	0	0.00	13352
327876	\N	David	Luger	4571	4276	2025-06-24 19:48:54.581559-05	nndz-WkNHeHhidi9ndz09	4511	t	18.70	7	8	46.70		2025-06-24 19:48:54.581559-05	0	0	0	0.00	13352
327877	\N	Adam	Morgan	4571	4276	2025-06-24 19:48:54.581559-05	nndz-WkNPd3hMeitodz09	4511	t	\N	14	2	87.50		2025-06-24 19:48:54.581559-05	0	0	0	0.00	13352
327878	\N	Brett	Stein	4571	4276	2025-06-24 19:48:54.581559-05	nndz-WkNDNnhyYjVoZz09	4511	t	20.40	8	7	53.30		2025-06-24 19:48:54.581559-05	0	0	0	0.00	13352
327879	\N	Mark	Schaefer	4590	4276	2025-06-24 19:48:54.581559-05	nndz-WkNPd3hMM3doUT09	4511	t	\N	14	16	46.70	C	2025-06-24 19:48:54.581559-05	0	0	0	0.00	13522
327880	\N	Ben	Williams	4590	4276	2025-06-24 19:48:54.581559-05	nndz-WkNPd3hMei9oUT09	4511	t	\N	2	4	33.30	CC	2025-06-24 19:48:54.581559-05	0	0	0	0.00	13522
327881	\N	Anthony	Appleyard	4590	4276	2025-06-24 19:48:54.581559-05	nndz-WkNDd3lMajdodz09	4511	t	\N	18	17	51.40		2025-06-24 19:48:54.581559-05	0	0	0	0.00	13522
327882	\N	Rob	Goeckel	4590	4276	2025-06-24 19:48:54.581559-05	nndz-WkNPd3hMM3dodz09	4511	t	13.40	11	6	64.70		2025-06-24 19:48:54.581559-05	0	0	0	0.00	13522
327883	\N	Matt	Lemery	4590	4276	2025-06-24 19:48:54.581559-05	nndz-WkNPd3hMdjZqUT09	4511	t	16.80	7	6	53.80		2025-06-24 19:48:54.581559-05	0	0	0	0.00	13522
327884	\N	Vince	Lombardi	4590	4276	2025-06-24 19:48:54.581559-05	nndz-WkNPd3hMci9odz09	4511	t	15.10	9	3	75.00		2025-06-24 19:48:54.581559-05	0	0	0	0.00	13522
327885	\N	Jon	Newlin	4590	4276	2025-06-24 19:48:54.581559-05	nndz-WkNPd3hMM3doZz09	4511	t	13.80	9	3	75.00		2025-06-24 19:48:54.581559-05	0	0	0	0.00	13522
327886	\N	John	Noell	4590	4276	2025-06-24 19:48:54.581559-05	nndz-WkNPd3hMbjdodz09	4511	t	12.90	12	8	60.00		2025-06-24 19:48:54.581559-05	0	0	0	0.00	13522
327887	\N	Reed	Schaefer	4590	4276	2025-06-24 19:48:54.581559-05	nndz-WkNPd3hMM3hqQT09	4511	t	11.50	8	3	72.70		2025-06-24 19:48:54.581559-05	0	0	0	0.00	13522
327888	\N	Andrew	Tomson	4590	4276	2025-06-24 19:48:54.581559-05	nndz-WkNPd3hMM3hnZz09	4511	t	11.90	7	8	46.70		2025-06-24 19:48:54.581559-05	0	0	0	0.00	13522
327889	\N	Audrius	Verbickas	4590	4276	2025-06-24 19:48:54.581559-05	nndz-WkNDNnhyYjVqUT09	4511	t	\N	9	9	50.00		2025-06-24 19:48:54.581559-05	0	0	0	0.00	13522
327890	\N	Colin	Zimmerman	4590	4276	2025-06-24 19:48:54.581559-05	nndz-WkNDNnlMYjVnQT09	4511	t	15.30	8	5	61.50		2025-06-24 19:48:54.581559-05	0	0	0	0.00	13522
327891	\N	Mike	Chabraja	4595	4276	2025-06-24 19:48:54.581559-05	nndz-WkNPd3hMeitqQT09	4511	t	17.10	7	8	46.70	C	2025-06-24 19:48:54.581559-05	0	0	0	0.00	13569
327892	\N	Bradford	Smith	4595	4276	2025-06-24 19:48:54.581559-05	nndz-WkNHL3hiLzRndz09	4511	t	\N	15	5	75.00	CC	2025-06-24 19:48:54.581559-05	0	0	0	0.00	13569
327893	\N	Chris	Baker	4595	4276	2025-06-24 19:48:54.581559-05	nndz-WkNPd3hMMy9oZz09	4511	t	13.00	5	8	38.50		2025-06-24 19:48:54.581559-05	0	0	0	0.00	13569
327894	\N	Lance	Carlson	4595	4276	2025-06-24 19:48:54.581559-05	nndz-WkNPd3hMYjRndz09	4511	t	26.20	3	11	21.40		2025-06-24 19:48:54.581559-05	0	0	0	0.00	13569
327895	\N	PJ	Carollo	4595	4276	2025-06-24 19:48:54.581559-05	nndz-WkNDd3lMLzlnQT09	4511	t	17.40	8	8	50.00		2025-06-24 19:48:54.581559-05	0	0	0	0.00	13569
327896	\N	Dan	Flagstad	4595	4276	2025-06-24 19:48:54.581559-05	nndz-WkNPd3hMMytqUT09	4511	t	26.90	0	4	0.00		2025-06-24 19:48:54.581559-05	0	0	0	0.00	13569
327897	\N	Mitch	Granger	4595	4276	2025-06-24 19:48:54.581559-05	nndz-WkNPd3hMMzRoQT09	4511	t	\N	12	5	70.60		2025-06-24 19:48:54.581559-05	0	0	0	0.00	13569
327898	\N	Andy	Graves	4595	4276	2025-06-24 19:48:54.581559-05	nndz-WkNPd3hMMytnZz09	4511	t	24.20	1	5	16.70		2025-06-24 19:48:54.581559-05	0	0	0	0.00	13569
327899	\N	Craig	Koppmann	4595	4276	2025-06-24 19:48:54.581559-05	nndz-WkNPd3hMdjZnUT09	4511	t	39.80	4	9	30.80		2025-06-24 19:48:54.581559-05	0	0	0	0.00	13569
327900	\N	Eric	Koppmann	4595	4276	2025-06-24 19:48:54.581559-05	nndz-WkNHN3dyZnhoUT09	4511	t	16.30	5	14	26.30		2025-06-24 19:48:54.581559-05	0	0	0	0.00	13569
327901	\N	Bill	Lambropoulos	4595	4276	2025-06-24 19:48:54.581559-05	nndz-WkNPd3hMbjZnQT09	4511	t	28.30	4	7	36.40		2025-06-24 19:48:54.581559-05	0	0	0	0.00	13569
327902	\N	John	Noble	4595	4276	2025-06-24 19:48:54.581559-05	nndz-WkNPd3hMeitqUT09	4511	t	\N	8	4	66.70		2025-06-24 19:48:54.581559-05	0	0	0	0.00	13569
327903	\N	Andrew	Ong	4595	4276	2025-06-24 19:48:54.581559-05	nndz-WkM2L3hMLzdqQT09	4511	t	\N	16	3	84.20		2025-06-24 19:48:54.581559-05	0	0	0	0.00	13569
327904	\N	Bill	Rogers	4595	4276	2025-06-24 19:48:54.581559-05	nndz-WkNPd3hMcjlnQT09	4511	t	24.30	10	5	66.70		2025-06-24 19:48:54.581559-05	0	0	0	0.00	13569
327905	\N	Henry	Crowe	4602	4276	2025-06-24 19:48:54.581559-05	nndz-WkNPd3hMbndnZz09	4511	t	13.10	10	7	58.80	C	2025-06-24 19:48:54.581559-05	0	0	0	0.00	13644
327906	\N	Peter	DeHaan	4602	4276	2025-06-24 19:48:54.581559-05	nndz-WkNPd3hMbjhqQT09	4511	t	21.00	7	6	53.80	CC	2025-06-24 19:48:54.581559-05	0	0	0	0.00	13644
327907	\N	Joseph	Connor	4602	4276	2025-06-24 19:48:54.581559-05	nndz-WkNPd3hMYjVoQT09	4511	t	22.20	4	7	36.40		2025-06-24 19:48:54.581559-05	0	0	0	0.00	13644
327908	\N	Brian	Faig	4602	4276	2025-06-24 19:48:54.581559-05	nndz-WkNHeHg3ditoQT09	4511	t	\N	15	11	57.70		2025-06-24 19:48:54.581559-05	0	0	0	0.00	13644
327909	\N	Jordan	Gottlieb	4602	4276	2025-06-24 19:48:54.581559-05	nndz-WkNPd3hMMzhoUT09	4511	t	\N	7	7	50.00		2025-06-24 19:48:54.581559-05	0	0	0	0.00	13644
327910	\N	Jamie	Green	4602	4276	2025-06-24 19:48:54.581559-05	nndz-WkNPd3hMM3dnZz09	4511	t	21.70	17	9	65.40		2025-06-24 19:48:54.581559-05	0	0	0	0.00	13644
327911	\N	Charlie	Howard	4602	4276	2025-06-24 19:48:54.581559-05	nndz-WkNPd3hMM3dnUT09	4511	t	\N	11	15	42.30		2025-06-24 19:48:54.581559-05	0	0	0	0.00	13644
327912	\N	Ben	Keating	4602	4276	2025-06-24 19:48:54.581559-05	nndz-WkM2L3hMYjVoZz09	4511	t	22.10	2	4	33.30		2025-06-24 19:48:54.581559-05	0	0	0	0.00	13644
327913	\N	Stephen	Larko	4602	4276	2025-06-24 19:48:54.581559-05	nndz-WkNPd3hMYjZqQT09	4511	t	12.40	20	19	51.30		2025-06-24 19:48:54.581559-05	0	0	0	0.00	13644
327914	\N	Connor	Parks	4602	4276	2025-06-24 19:48:54.581559-05	nndz-WkNHNHc3djloQT09	4511	t	11.80	9	4	69.20		2025-06-24 19:48:54.581559-05	0	0	0	0.00	13644
327915	\N	Peter	Stellas Jr	4602	4276	2025-06-24 19:48:54.581559-05	nndz-WkNDNnhydjVndz09	4511	t	\N	15	9	62.50		2025-06-24 19:48:54.581559-05	0	0	0	0.00	13644
327916	\N	Sean	Weber	4602	4276	2025-06-24 19:48:54.581559-05	nndz-WlNhL3dycjRqQT09	4511	t	\N	10	5	66.70		2025-06-24 19:48:54.581559-05	0	0	0	0.00	13644
327917	\N	Eddie	Trapp	4608	4276	2025-06-24 19:48:54.581559-05	nndz-WkNHNXdiajhoQT09	4511	t	\N	18	14	56.20	C	2025-06-24 19:48:54.581559-05	0	0	0	0.00	13669
327918	\N	George	Trapp	4608	4276	2025-06-24 19:48:54.581559-05	nndz-WkNPd3hMajZnUT09	4511	t	24.50	3	10	23.10	CC	2025-06-24 19:48:54.581559-05	0	0	0	0.00	13669
327919	\N	Connor	Casas	4608	4276	2025-06-24 19:48:54.581559-05	nndz-WkNDNnhyYjZoQT09	4511	t	15.60	15	7	68.20		2025-06-24 19:48:54.581559-05	0	0	0	0.00	13669
327920	\N	Sasha	Djordjevic	4608	4276	2025-06-24 19:48:54.581559-05	nndz-WkNPd3hMMzVnUT09	4511	t	\N	7	8	46.70		2025-06-24 19:48:54.581559-05	0	0	0	0.00	13669
327921	\N	Andy	Goodrich	4608	4276	2025-06-24 19:48:54.581559-05	nndz-WkNPd3hMdi9odz09	4511	t	16.20	6	10	37.50		2025-06-24 19:48:54.581559-05	0	0	0	0.00	13669
327922	\N	Matt	Harris	4608	4276	2025-06-24 19:48:54.581559-05	nndz-WkNPd3hMajZoZz09	4511	t	12.20	16	19	45.70		2025-06-24 19:48:54.581559-05	0	0	0	0.00	13669
327923	\N	John	M Weinlader	4608	4276	2025-06-24 19:48:54.581559-05	nndz-WkNPd3g3djlnUT09	4511	t	26.40	11	14	44.00		2025-06-24 19:48:54.581559-05	0	0	0	0.00	13669
327924	\N	Daniel	McGuire	4608	4276	2025-06-24 19:48:54.581559-05	nndz-WkNPd3hMcnhndz09	4511	t	13.40	10	7	58.80		2025-06-24 19:48:54.581559-05	0	0	0	0.00	13669
327925	\N	Danny	Oaks	4608	4276	2025-06-24 19:48:54.581559-05	nndz-WkNDNnlMaitndz09	4511	t	\N	13	15	46.40		2025-06-24 19:48:54.581559-05	0	0	0	0.00	13669
327926	\N	Mick	Parks	4608	4276	2025-06-24 19:48:54.581559-05	nndz-WkNPd3hMcjZqQT09	4511	t	\N	13	13	50.00		2025-06-24 19:48:54.581559-05	0	0	0	0.00	13669
327927	\N	John	Watrous	4608	4276	2025-06-24 19:48:54.581559-05	nndz-WkNPd3hMcjdnUT09	4511	t	20.50	13	11	54.20		2025-06-24 19:48:54.581559-05	0	0	0	0.00	13669
327928	\N	James	Goldman	4632	4276	2025-06-24 19:48:54.581559-05	nndz-WkNPd3hMejhqUT09	4511	t	\N	9	6	60.00	C	2025-06-24 19:48:54.581559-05	0	0	0	0.00	13853
327929	\N	Carl	Bartholomay	4632	4276	2025-06-24 19:48:54.581559-05	nndz-WkNPd3hMM3dqUT09	4511	t	18.20	6	14	30.00		2025-06-24 19:48:54.581559-05	0	0	0	0.00	13853
327930	\N	Tom	Concklin	4632	4276	2025-06-24 19:48:54.581559-05	nndz-WkMrK3dMbndnQT09	4511	t	13.40	18	6	75.00		2025-06-24 19:48:54.581559-05	0	0	0	0.00	13853
327931	\N	Paul	Garvin	4632	4276	2025-06-24 19:48:54.581559-05	nndz-WkNPd3hMei9oZz09	4511	t	\N	6	7	46.20		2025-06-24 19:48:54.581559-05	0	0	0	0.00	13853
327932	\N	Harold	Martin	4632	4276	2025-06-24 19:48:54.581559-05	nndz-WkNPd3hMYjZnUT09	4511	t	10.90	15	9	62.50		2025-06-24 19:48:54.581559-05	0	0	0	0.00	13853
327933	\N	Ryan	Mullaney III	4632	4276	2025-06-24 19:48:54.581559-05	nndz-WkNPd3hMMzZnQT09	4511	t	\N	16	11	59.30		2025-06-24 19:48:54.581559-05	0	0	0	0.00	13853
327934	\N	Connor	Roth	4632	4276	2025-06-24 19:48:54.581559-05	nndz-WkNPd3hMei9ndz09	4511	t	10.60	18	8	69.20		2025-06-24 19:48:54.581559-05	0	0	0	0.00	13853
327935	\N	Todd	Schaefer	4632	4276	2025-06-24 19:48:54.581559-05	nndz-WkNPd3hMcjhodz09	4511	t	\N	7	9	43.80		2025-06-24 19:48:54.581559-05	0	0	0	0.00	13853
327936	\N	Van	Stapleton	4632	4276	2025-06-24 19:48:54.581559-05	nndz-WkNPd3hMMzhnQT09	4511	t	22.20	1	0	100.00		2025-06-24 19:48:54.581559-05	0	0	0	0.00	13853
327937	\N	Pat	Usher	4632	4276	2025-06-24 19:48:54.581559-05	nndz-WkNPd3hMMzZoZz09	4511	t	18.80	8	9	47.10		2025-06-24 19:48:54.581559-05	0	0	0	0.00	13853
327938	\N	Brian	Panek	4637	4276	2025-06-24 19:48:54.581559-05	nndz-WkNPd3hMenhqUT09	4511	t	\N	17	7	70.80	C	2025-06-24 19:48:54.581559-05	0	0	0	0.00	13909
327939	\N	Kevin	Weasler	4637	4276	2025-06-24 19:48:54.581559-05	nndz-WkNPd3hMdjlndz09	4511	t	23.60	4	5	44.40	CC	2025-06-24 19:48:54.581559-05	0	0	0	0.00	13909
327940	\N	Peter	Berka	4637	4276	2025-06-24 19:48:54.581559-05	nndz-WkNPd3hMMzVqQT09	4511	t	\N	21	8	72.40		2025-06-24 19:48:54.581559-05	0	0	0	0.00	13909
327941	\N	Doug	Clingan	4637	4276	2025-06-24 19:48:54.581559-05	nndz-WkNPd3hMdjZqQT09	4511	t	16.70	10	9	52.60		2025-06-24 19:48:54.581559-05	0	0	0	0.00	13909
327942	\N	Kian	Dowlatshahi	4637	4276	2025-06-24 19:48:54.581559-05	nndz-WkNHNXdMcjVqUT09	4511	t	16.80	16	6	72.70		2025-06-24 19:48:54.581559-05	0	0	0	0.00	13909
327943	\N	Luke	Figora	4637	4276	2025-06-24 19:48:54.581559-05	nndz-WkNPd3hMMy9qQT09	4511	t	19.30	10	7	58.80		2025-06-24 19:48:54.581559-05	0	0	0	0.00	13909
327944	\N	Radek	Guzik	4637	4276	2025-06-24 19:48:54.581559-05	nndz-WkNPd3hMejhndz09	4511	t	14.80	11	15	42.30		2025-06-24 19:48:54.581559-05	0	0	0	0.00	13909
327945	\N	Scott	Mansager	4637	4276	2025-06-24 19:48:54.581559-05	nndz-WkNPd3hMendoQT09	4511	t	\N	14	3	82.40		2025-06-24 19:48:54.581559-05	0	0	0	0.00	13909
327946	\N	Jonas	Merckx	4637	4276	2025-06-24 19:48:54.581559-05	nndz-WkM2L3g3andnZz09	4511	t	\N	30	3	90.90		2025-06-24 19:48:54.581559-05	0	0	0	0.00	13909
327947	\N	Darryl	Silverman	4637	4276	2025-06-24 19:48:54.581559-05	nndz-WkNPd3liZnhodz09	4511	t	12.90	13	7	65.00		2025-06-24 19:48:54.581559-05	0	0	0	0.00	13909
327948	\N	Brian	Leydon	4639	4276	2025-06-24 19:48:54.581559-05	nndz-WkNPd3hMcjdndz09	4511	t	16.00	8	9	47.10	C	2025-06-24 19:48:54.581559-05	0	0	0	0.00	13968
327949	\N	Jerry	Ehlinger	4639	4276	2025-06-24 19:48:54.581559-05	nndz-WkNPd3hMZjdnZz09	4511	t	25.10	8	21	27.60		2025-06-24 19:48:54.581559-05	0	0	0	0.00	13968
327950	\N	David	Halpern	4639	4276	2025-06-24 19:48:54.581559-05	nndz-WkNPd3hycjZnZz09	4511	t	24.40	3	4	42.90		2025-06-24 19:48:54.581559-05	0	0	0	0.00	13968
327951	\N	Adam	Herakovich	4639	4276	2025-06-24 19:48:54.581559-05	nndz-WkNPd3hMcndnZz09	4511	t	15.50	6	5	54.50		2025-06-24 19:48:54.581559-05	0	0	0	0.00	13968
327952	\N	Scott	Hill	4639	4276	2025-06-24 19:48:54.581559-05	nndz-WkNPd3hMdjRqQT09	4511	t	\N	20	10	66.70		2025-06-24 19:48:54.581559-05	0	0	0	0.00	13968
327953	\N	Jim	Kozak	4639	4276	2025-06-24 19:48:54.581559-05	nndz-WkNPd3hMMzRodz09	4511	t	12.50	6	4	60.00		2025-06-24 19:48:54.581559-05	0	0	0	0.00	13968
327954	\N	Robert	Krill	4639	4276	2025-06-24 19:48:54.581559-05	nndz-WkM2L3hyZjRoZz09	4511	t	\N	0	0	0.00		2025-06-24 19:48:54.581559-05	0	0	0	0.00	13968
327955	\N	Mike	Marino	4639	4276	2025-06-24 19:48:54.581559-05	nndz-WkNPd3hMMzRqQT09	4511	t	\N	6	6	50.00		2025-06-24 19:48:54.581559-05	0	0	0	0.00	13968
327956	\N	Nick	Marino	4639	4276	2025-06-24 19:48:54.581559-05	nndz-WkMrK3hiendqQT09	4511	t	17.30	2	7	22.20		2025-06-24 19:48:54.581559-05	0	0	0	0.00	13968
327957	\N	Tim	Miller	4639	4276	2025-06-24 19:48:54.581559-05	nndz-WkNPd3hMcndnQT09	4511	t	22.00	3	6	33.30		2025-06-24 19:48:54.581559-05	0	0	0	0.00	13968
327958	\N	Mackey	Pierce	4639	4276	2025-06-24 19:48:54.581559-05	nndz-WkNPd3hMei9nUT09	4511	t	\N	19	16	54.30		2025-06-24 19:48:54.581559-05	0	0	0	0.00	13968
327959	\N	Greg	Wotring	4639	4276	2025-06-24 19:48:54.581559-05	nndz-WkNPd3hMMzVnQT09	4511	t	\N	16	9	64.00		2025-06-24 19:48:54.581559-05	0	0	0	0.00	13968
327960	\N	Stu	Bradley	4640	4276	2025-06-24 19:48:54.581559-05	nndz-WkNPd3hMMytnQT09	4511	t	\N	7	6	53.80	C	2025-06-24 19:48:54.581559-05	0	0	0	0.00	13995
327961	\N	Tom	Moore	4640	4276	2025-06-24 19:48:54.581559-05	nndz-WkNPd3hMMzZndz09	4511	t	\N	12	13	48.00	CC	2025-06-24 19:48:54.581559-05	0	0	0	0.00	13995
327962	\N	Teddy	Boucquemont	4640	4276	2025-06-24 19:48:54.581559-05	nndz-WkNPd3hMenhoUT09	4511	t	\N	0	0	0.00		2025-06-24 19:48:54.581559-05	0	0	0	0.00	13995
327963	\N	David	Bukowski	4640	4276	2025-06-24 19:48:54.581559-05	nndz-WkNPd3hMendoZz09	4511	t	\N	12	7	63.20		2025-06-24 19:48:54.581559-05	0	0	0	0.00	13995
327964	\N	Tom	Davis	4640	4276	2025-06-24 19:48:54.581559-05	nndz-WkNPd3hMcjhoQT09	4511	t	14.80	6	6	50.00		2025-06-24 19:48:54.581559-05	0	0	0	0.00	13995
327965	\N	Dave	Fritzsche	4640	4276	2025-06-24 19:48:54.581559-05	nndz-WkNPd3hMMzdodz09	4511	t	\N	16	14	53.30		2025-06-24 19:48:54.581559-05	0	0	0	0.00	13995
327966	\N	JP	Gallagher	4640	4276	2025-06-24 19:48:54.581559-05	nndz-WkNPd3hMcjhnZz09	4511	t	15.40	13	7	65.00		2025-06-24 19:48:54.581559-05	0	0	0	0.00	13995
327967	\N	Jeremy	Shull	4640	4276	2025-06-24 19:48:54.581559-05	nndz-WkNPd3hMM3hnUT09	4511	t	12.30	10	6	62.50		2025-06-24 19:48:54.581559-05	0	0	0	0.00	13995
327968	\N	Tom	Morton	4644	4276	2025-06-24 19:48:54.581559-05	nndz-WkNPd3hMMytodz09	4511	t	11.90	7	9	43.80	C	2025-06-24 19:48:54.581559-05	0	0	0	0.00	14050
327969	\N	Dan	Rosenberg	4644	4276	2025-06-24 19:48:54.581559-05	nndz-WkNPd3g3NzRnZz09	4511	t	\N	9	15	37.50	CC	2025-06-24 19:48:54.581559-05	0	0	0	0.00	14050
327970	\N	Mark	Baby	4644	4276	2025-06-24 19:48:54.581559-05	nndz-WkNPd3g3NzdoUT09	4511	t	21.30	3	6	33.30		2025-06-24 19:48:54.581559-05	0	0	0	0.00	14050
327971	\N	Brooks	Harding	4644	4276	2025-06-24 19:48:54.581559-05	nndz-WkNPd3hMYi9qUT09	4511	t	22.00	2	2	50.00		2025-06-24 19:48:54.581559-05	0	0	0	0.00	14050
327972	\N	Ben	Kimmel	4644	4276	2025-06-24 19:48:54.581559-05	nndz-WkNPd3hMMytoZz09	4511	t	\N	9	11	45.00		2025-06-24 19:48:54.581559-05	0	0	0	0.00	14050
327973	\N	Trever	Koek	4644	4276	2025-06-24 19:48:54.581559-05	nndz-WkNPd3g3NytoQT09	4511	t	12.30	9	7	56.20		2025-06-24 19:48:54.581559-05	0	0	0	0.00	14050
327974	\N	Daniel	Levine	4644	4276	2025-06-24 19:48:54.581559-05	nndz-WkNHeHc3bnhqUT09	4511	t	\N	12	16	42.90		2025-06-24 19:48:54.581559-05	0	0	0	0.00	14050
327975	\N	Tom	McNeela	4644	4276	2025-06-24 19:48:54.581559-05	nndz-WkNPd3hMMytoQT09	4511	t	13.70	5	2	71.40		2025-06-24 19:48:54.581559-05	0	0	0	0.00	14050
327976	\N	Wally	Pfenning	4644	4276	2025-06-24 19:48:54.581559-05	nndz-WkNHd3dyMzhnZz09	4511	t	11.50	9	9	50.00		2025-06-24 19:48:54.581559-05	0	0	0	0.00	14050
327977	\N	Addom	Powell	4644	4276	2025-06-24 19:48:54.581559-05	nndz-WkNPd3hMbjloZz09	4511	t	18.80	14	9	60.90		2025-06-24 19:48:54.581559-05	0	0	0	0.00	14050
327978	\N	John	Silk	4644	4276	2025-06-24 19:48:54.581559-05	nndz-WkNPd3hMMzdoUT09	4511	t	\N	8	9	47.10		2025-06-24 19:48:54.581559-05	0	0	0	0.00	14050
327979	\N	Mike	Wilkins	4644	4276	2025-06-24 19:48:54.581559-05	nndz-WkNPd3hMMzdoZz09	4511	t	14.30	10	7	58.80		2025-06-24 19:48:54.581559-05	0	0	0	0.00	14050
327980	\N	Jason	Stanislaw	4645	4276	2025-06-24 19:48:54.581559-05	nndz-WkNPd3hMcndodz09	4511	t	24.20	7	16	30.40	C	2025-06-24 19:48:54.581559-05	0	0	0	0.00	14062
327981	\N	Mark	Baladad	4645	4276	2025-06-24 19:48:54.581559-05	nndz-WkNPd3hMcnhnUT09	4511	t	17.70	2	12	14.30		2025-06-24 19:48:54.581559-05	0	0	0	0.00	14062
327982	\N	Paul	Buckingham	4645	4276	2025-06-24 19:48:54.581559-05	nndz-WkNPd3hMditoUT09	4511	t	\N	2	2	50.00		2025-06-24 19:48:54.581559-05	0	0	0	0.00	14062
327983	\N	Casey	Conaghan	4645	4276	2025-06-24 19:48:54.581559-05	nndz-WkNPd3hMcnhnQT09	4511	t	22.70	3	7	30.00		2025-06-24 19:48:54.581559-05	0	0	0	0.00	14062
327984	\N	Mike	Haber	4645	4276	2025-06-24 19:48:54.581559-05	nndz-WkNPd3hMMy9qUT09	4511	t	27.10	0	1	0.00		2025-06-24 19:48:54.581559-05	0	0	0	0.00	14062
327985	\N	Charles	Leger	4645	4276	2025-06-24 19:48:54.581559-05	nndz-WkNPd3hMenhoQT09	4511	t	11.10	0	5	0.00		2025-06-24 19:48:54.581559-05	0	0	0	0.00	14062
327986	\N	Anthony	McPherson	4645	4276	2025-06-24 19:48:54.581559-05	nndz-WkNPd3hMei9qUT09	4511	t	\N	19	10	65.50		2025-06-24 19:48:54.581559-05	0	0	0	0.00	14062
327987	\N	Eric	Moran	4645	4276	2025-06-24 19:48:54.581559-05	nndz-WkNPd3hMenhnUT09	4511	t	23.70	0	8	0.00		2025-06-24 19:48:54.581559-05	0	0	0	0.00	14062
327988	\N	Mike	Morrison	4645	4276	2025-06-24 19:48:54.581559-05	nndz-WkNPd3hMdjdodz09	4511	t	20.40	5	5	50.00		2025-06-24 19:48:54.581559-05	0	0	0	0.00	14062
327989	\N	Bill	Plain	4645	4276	2025-06-24 19:48:54.581559-05	nndz-WkNPd3hMai9ndz09	4511	t	24.50	4	12	25.00		2025-06-24 19:48:54.581559-05	0	0	0	0.00	14062
327990	\N	Eric	Pohl	4645	4276	2025-06-24 19:48:54.581559-05	nndz-WkNDOXhyLytoZz09	4511	t	\N	23	10	69.70		2025-06-24 19:48:54.581559-05	0	0	0	0.00	14062
327991	\N	Scott	Reighard	4645	4276	2025-06-24 19:48:54.581559-05	nndz-WkNPd3hMcndoQT09	4511	t	27.30	3	12	20.00		2025-06-24 19:48:54.581559-05	0	0	0	0.00	14062
327992	\N	Krishin	Shivdasani	4645	4276	2025-06-24 19:48:54.581559-05	nndz-WkNDOXdidjhqQT09	4511	t	15.60	6	9	40.00		2025-06-24 19:48:54.581559-05	0	0	0	0.00	14062
327993	\N	Mike	Sims	4645	4276	2025-06-24 19:48:54.581559-05	nndz-WkNDNnhyYjVnQT09	4511	t	\N	23	10	69.70		2025-06-24 19:48:54.581559-05	0	0	0	0.00	14062
327994	\N	Rob	Zumph	4645	4276	2025-06-24 19:48:54.581559-05	nndz-WkNPd3hMdjdndz09	4511	t	21.80	1	5	16.70		2025-06-24 19:48:54.581559-05	0	0	0	0.00	14062
327995	\N	Brett	Binkley	4646	4276	2025-06-24 19:48:54.581559-05	nndz-WkNHeHhMN3dnZz09	4511	t	\N	7	8	46.70	C	2025-06-24 19:48:54.581559-05	0	0	0	0.00	14077
327996	\N	Brian	Saltzman	4646	4276	2025-06-24 19:48:54.581559-05	nndz-WkNDOXdiajVoZz09	4511	t	14.60	8	5	61.50	CC	2025-06-24 19:48:54.581559-05	0	0	0	0.00	14077
327997	\N	Michael	Benson	4646	4276	2025-06-24 19:48:54.581559-05	nndz-WkNPd3g3LzVndz09	4511	t	16.10	11	7	61.10		2025-06-24 19:48:54.581559-05	0	0	0	0.00	14077
327998	\N	Ryan	Botjer	4646	4276	2025-06-24 19:48:54.581559-05	nndz-WkNHeHdybitoQT09	4511	t	16.20	5	4	55.60		2025-06-24 19:48:54.581559-05	0	0	0	0.00	14077
327999	\N	Vineeth	Gossain	4646	4276	2025-06-24 19:48:54.581559-05	nndz-WkNPd3hMM3hqUT09	4511	t	\N	7	7	50.00		2025-06-24 19:48:54.581559-05	0	0	0	0.00	14077
328000	\N	Peter	Hammond	4646	4276	2025-06-24 19:48:54.581559-05	nndz-WkNPd3hMajVodz09	4511	t	11.40	10	8	55.60		2025-06-24 19:48:54.581559-05	0	0	0	0.00	14077
328001	\N	Arun	Jagasia	4646	4276	2025-06-24 19:48:54.581559-05	nndz-WkNDNnlMYjRodz09	4511	t	10.10	16	16	50.00		2025-06-24 19:48:54.581559-05	0	0	0	0.00	14077
328002	\N	Josh	Kritzler	4646	4276	2025-06-24 19:48:54.581559-05	nndz-WkNPd3hMMzdqQT09	4511	t	\N	8	12	40.00		2025-06-24 19:48:54.581559-05	0	0	0	0.00	14077
328003	\N	Jeff	Rightnour	4646	4276	2025-06-24 19:48:54.581559-05	nndz-WkMrK3hiNzZoUT09	4511	t	\N	9	10	47.40		2025-06-24 19:48:54.581559-05	0	0	0	0.00	14077
328004	\N	Jay	Woldenberg	4646	4276	2025-06-24 19:48:54.581559-05	nndz-WkNPd3hMendnZz09	4511	t	\N	7	13	35.00		2025-06-24 19:48:54.581559-05	0	0	0	0.00	14077
328005	\N	David	Zak	4646	4276	2025-06-24 19:48:54.581559-05	nndz-WkM2NXdiMzlndz09	4511	t	\N	16	9	64.00		2025-06-24 19:48:54.581559-05	0	0	0	0.00	14077
328006	\N	Bob	Ernst	4579	4292	2025-06-24 19:48:54.581559-05	nndz-WkNPd3hMcjdqQT09	4511	t	29.20	7	8	46.70	C	2025-06-24 19:48:54.581559-05	0	0	0	0.00	13423
328007	\N	Ben	Dooley	4579	4292	2025-06-24 19:48:54.581559-05	nndz-WkNPd3hMbjlnZz09	4511	t	26.20	1	8	11.10	CC	2025-06-24 19:48:54.581559-05	0	0	0	0.00	13423
328008	\N	Mike	Abrahamson	4579	4292	2025-06-24 19:48:54.581559-05	nndz-WkNPd3hMcjdoZz09	4511	t	19.80	10	4	71.40		2025-06-24 19:48:54.581559-05	0	0	0	0.00	13423
328009	\N	Alan	Hutchinson	4579	4292	2025-06-24 19:48:54.581559-05	nndz-WkNPd3hMcjlnZz09	4511	t	27.10	2	1	66.70		2025-06-24 19:48:54.581559-05	0	0	0	0.00	13423
328010	\N	Tim	Junker	4579	4292	2025-06-24 19:48:54.581559-05	nndz-WkNPd3hMcjdoUT09	4511	t	27.60	8	8	50.00		2025-06-24 19:48:54.581559-05	0	0	0	0.00	13423
328011	\N	Dave	McHugh	4579	4292	2025-06-24 19:48:54.581559-05	nndz-WkNPd3g3YjhnZz09	4511	t	18.60	16	10	61.50		2025-06-24 19:48:54.581559-05	0	0	0	0.00	13423
328012	\N	Dennis	Moore	4579	4292	2025-06-24 19:48:54.581559-05	nndz-WkNPd3hMcjdnQT09	4511	t	25.10	3	4	42.90		2025-06-24 19:48:54.581559-05	0	0	0	0.00	13423
328013	\N	Matthew	Naughton	4579	4292	2025-06-24 19:48:54.581559-05	nndz-WkNPd3g3M3dqQT09	4511	t	22.70	4	9	30.80		2025-06-24 19:48:54.581559-05	0	0	0	0.00	13423
328014	\N	Greg	Neidballa	4579	4292	2025-06-24 19:48:54.581559-05	nndz-WkNPd3hMbi9oUT09	4511	t	24.70	0	0	0.00		2025-06-24 19:48:54.581559-05	0	0	0	0.00	13423
328015	\N	Robb	Rickett	4579	4292	2025-06-24 19:48:54.581559-05	nndz-WkNPd3hMcjdodz09	4511	t	\N	12	4	75.00		2025-06-24 19:48:54.581559-05	0	0	0	0.00	13423
328016	\N	Connor	Roth	4579	4292	2025-06-24 19:48:54.581559-05	nndz-WkNPd3hMei9ndz09	4511	t	10.60	18	8	69.20		2025-06-24 19:48:54.581559-05	0	0	0	0.00	13423
328017	\N	Dane	Schmidgall	4579	4292	2025-06-24 19:48:54.581559-05	nndz-WkNPd3hMenhndz09	4511	t	\N	16	4	80.00		2025-06-24 19:48:54.581559-05	0	0	0	0.00	13423
328018	\N	John	Watrous	4579	4292	2025-06-24 19:48:54.581559-05	nndz-WkNPd3hMcjdnUT09	4511	t	20.50	13	11	54.20		2025-06-24 19:48:54.581559-05	0	0	0	0.00	13423
328019	\N	Patrick	Bouchard	4581	4292	2025-06-24 19:48:54.581559-05	nndz-WkNPd3hManhqQT09	4511	t	17.40	7	16	30.40	C	2025-06-24 19:48:54.581559-05	0	0	0	0.00	13458
328020	\N	Carl	Bartholomay	4581	4292	2025-06-24 19:48:54.581559-05	nndz-WkNPd3hMM3dqUT09	4511	t	18.20	6	14	30.00		2025-06-24 19:48:54.581559-05	0	0	0	0.00	13458
328021	\N	Eddie	DeLaCruz	4581	4292	2025-06-24 19:48:54.581559-05	nndz-WkNPd3hMMzloZz09	4511	t	10.80	9	11	45.00		2025-06-24 19:48:54.581559-05	0	0	0	0.00	13458
328022	\N	Chris	Mayer	4581	4292	2025-06-24 19:48:54.581559-05	nndz-WkNPd3hMcjVodz09	4511	t	18.30	10	3	76.90		2025-06-24 19:48:54.581559-05	0	0	0	0.00	13458
328023	\N	Vince	McPherson	4581	4292	2025-06-24 19:48:54.581559-05	nndz-WkNDd3g3Zjhodz09	4511	t	22.20	6	3	66.70		2025-06-24 19:48:54.581559-05	0	0	0	0.00	13458
328024	\N	Jim	Nelson	4581	4292	2025-06-24 19:48:54.581559-05	nndz-WkNPd3hMcjVndz09	4511	t	17.10	7	4	63.60		2025-06-24 19:48:54.581559-05	0	0	0	0.00	13458
328025	\N	Todd	Nelson	4581	4292	2025-06-24 19:48:54.581559-05	nndz-WkNPd3hMM3dqQT09	4511	t	18.20	7	5	58.30		2025-06-24 19:48:54.581559-05	0	0	0	0.00	13458
328026	\N	Charlie	Pfister	4581	4292	2025-06-24 19:48:54.581559-05	nndz-WkNPd3hMei9qQT09	4511	t	18.90	10	8	55.60		2025-06-24 19:48:54.581559-05	0	0	0	0.00	13458
328027	\N	Blake	Schafer	4581	4292	2025-06-24 19:48:54.581559-05	nndz-WkNPd3g3LzdoUT09	4511	t	17.40	10	3	76.90		2025-06-24 19:48:54.581559-05	0	0	0	0.00	13458
328028	\N	Jason	Schleinzer	4581	4292	2025-06-24 19:48:54.581559-05	nndz-WkNPd3g3ejlnUT09	4511	t	19.60	13	4	76.50		2025-06-24 19:48:54.581559-05	0	0	0	0.00	13458
328029	\N	Christopher	Williams	4585	4292	2025-06-24 19:48:54.581559-05	nndz-WkNPd3hMMzRndz09	4511	t	17.30	5	20	20.00	C	2025-06-24 19:48:54.581559-05	0	0	0	0.00	13484
328030	\N	Andrew	Cupps	4585	4292	2025-06-24 19:48:54.581559-05	nndz-WkNPd3hMajVnUT09	4511	t	22.20	5	13	27.80		2025-06-24 19:48:54.581559-05	0	0	0	0.00	13484
328031	\N	Connor	Dawson	4585	4292	2025-06-24 19:48:54.581559-05	nndz-WkNDNnhyYi9qUT09	4511	t	15.20	0	1	0.00		2025-06-24 19:48:54.581559-05	0	0	0	0.00	13484
328032	\N	Nelson	Head	4585	4292	2025-06-24 19:48:54.581559-05	nndz-WkNPd3hMMzhqUT09	4511	t	27.70	1	9	10.00		2025-06-24 19:48:54.581559-05	0	0	0	0.00	13484
328033	\N	Jack	Howell	4585	4292	2025-06-24 19:48:54.581559-05	nndz-WkNDOHg3MytqQT09	4511	t	19.20	0	1	0.00		2025-06-24 19:48:54.581559-05	0	0	0	0.00	13484
328034	\N	Taylor	Katzman	4585	4292	2025-06-24 19:48:54.581559-05	nndz-WkNHNXdiMzdndz09	4511	t	26.10	2	9	18.20		2025-06-24 19:48:54.581559-05	0	0	0	0.00	13484
328035	\N	Ross	Landman	4585	4292	2025-06-24 19:48:54.581559-05	nndz-WkNPd3hMMzlqQT09	4511	t	27.60	2	12	14.30		2025-06-24 19:48:54.581559-05	0	0	0	0.00	13484
328036	\N	Nick	Lawler	4585	4292	2025-06-24 19:48:54.581559-05	nndz-WkNPd3hMMzRnZz09	4511	t	28.60	0	0	0.00		2025-06-24 19:48:54.581559-05	0	0	0	0.00	13484
328037	\N	Dave	Polayes	4585	4292	2025-06-24 19:48:54.581559-05	nndz-WkNPd3hMMzVndz09	4511	t	22.90	4	14	22.20		2025-06-24 19:48:54.581559-05	0	0	0	0.00	13484
328038	\N	Dan	Shapiro	4585	4292	2025-06-24 19:48:54.581559-05	nndz-WkNHNXhyN3dodz09	4511	t	21.10	3	14	17.60		2025-06-24 19:48:54.581559-05	0	0	0	0.00	13484
328039	\N	Matt	Thornton	4585	4292	2025-06-24 19:48:54.581559-05	nndz-WkNPd3hMMzhqQT09	4511	t	24.20	1	6	14.30		2025-06-24 19:48:54.581559-05	0	0	0	0.00	13484
328040	\N	Dan	Williams	4585	4292	2025-06-24 19:48:54.581559-05	nndz-WkNPd3hMMy9nUT09	4511	t	29.70	1	2	33.30		2025-06-24 19:48:54.581559-05	0	0	0	0.00	13484
328041	\N	David	Williams	4585	4292	2025-06-24 19:48:54.581559-05	nndz-WkNPd3hMMzloQT09	4511	t	19.60	4	12	25.00		2025-06-24 19:48:54.581559-05	0	0	0	0.00	13484
328042	\N	Arun	Jagasia	4587	4292	2025-06-24 19:48:54.581559-05	nndz-WkNDNnlMYjRodz09	4511	t	10.10	16	16	50.00	C	2025-06-24 19:48:54.581559-05	0	0	0	0.00	13507
328043	\N	Eric	Schulman	4587	4292	2025-06-24 19:48:54.581559-05	nndz-WkNPd3hyNzRndz09	4511	t	19.90	20	15	57.10	CC	2025-06-24 19:48:54.581559-05	0	0	0	0.00	13507
328044	\N	Blake	Bazarnik	4587	4292	2025-06-24 19:48:54.581559-05	nndz-WkM2L3dyLy9ndz09	4511	t	20.30	5	7	41.70		2025-06-24 19:48:54.581559-05	0	0	0	0.00	13507
328045	\N	Jason	Gunther	4587	4292	2025-06-24 19:48:54.581559-05	nndz-WkNHeHg3djhoZz09	4511	t	17.00	15	15	50.00		2025-06-24 19:48:54.581559-05	0	0	0	0.00	13507
328046	\N	Nate	Helmkamp	4587	4292	2025-06-24 19:48:54.581559-05	nndz-WkNDd3lMYjRnUT09	4511	t	25.80	6	10	37.50		2025-06-24 19:48:54.581559-05	0	0	0	0.00	13507
328047	\N	Todd	Leistner	4587	4292	2025-06-24 19:48:54.581559-05	nndz-WkNPd3hMdjVoZz09	4511	t	20.70	9	6	60.00		2025-06-24 19:48:54.581559-05	0	0	0	0.00	13507
328048	\N	Noah	Seidenberg	4587	4292	2025-06-24 19:48:54.581559-05	nndz-WkNPd3hMcndoZz09	4511	t	31.50	10	8	55.60		2025-06-24 19:48:54.581559-05	0	0	0	0.00	13507
328049	\N	Ben	Van Dixhorn	4587	4292	2025-06-24 19:48:54.581559-05	nndz-WkMrK3hiajlodz09	4511	t	15.20	5	3	62.50		2025-06-24 19:48:54.581559-05	0	0	0	0.00	13507
328050	\N	Jack	VanDixhorn	4587	4292	2025-06-24 19:48:54.581559-05	nndz-WlNhOXhMLy9oUT09	4511	t	26.90	7	6	53.80		2025-06-24 19:48:54.581559-05	0	0	0	0.00	13507
328051	\N	David	Zak	4587	4292	2025-06-24 19:48:54.581559-05	nndz-WkM2NXdiMzlndz09	4511	t	\N	16	9	64.00		2025-06-24 19:48:54.581559-05	0	0	0	0.00	13507
328052	\N	Kevin	Gerow	4588	4292	2025-06-24 19:48:54.581559-05	nndz-WkNDOHhMM3dqUT09	4511	t	28.00	10	7	58.80	C	2025-06-24 19:48:54.581559-05	0	0	0	0.00	13511
328053	\N	Tom	Concklin	4588	4292	2025-06-24 19:48:54.581559-05	nndz-WkMrK3dMbndnQT09	4511	t	13.40	18	6	75.00		2025-06-24 19:48:54.581559-05	0	0	0	0.00	13511
328054	\N	Eddie	Grabill	4588	4292	2025-06-24 19:48:54.581559-05	nndz-WlNlN3lMejhnZz09	4511	t	36.40	1	2	33.30		2025-06-24 19:48:54.581559-05	0	0	0	0.00	13511
328055	\N	Ryan	Keefe	4588	4292	2025-06-24 19:48:54.581559-05	nndz-WkNHeHc3Zi9oQT09	4511	t	10.00	20	7	74.10		2025-06-24 19:48:54.581559-05	0	0	0	0.00	13511
328056	\N	Kerry	Koranda	4588	4292	2025-06-24 19:48:54.581559-05	nndz-WkNPd3hMdjloUT09	4511	t	25.60	6	8	42.90		2025-06-24 19:48:54.581559-05	0	0	0	0.00	13511
328057	\N	Clay	Leonard	4588	4292	2025-06-24 19:48:54.581559-05	nndz-WkNPd3hMdjloQT09	4511	t	22.20	8	11	42.10		2025-06-24 19:48:54.581559-05	0	0	0	0.00	13511
328058	\N	Andrew	Lockhart	4588	4292	2025-06-24 19:48:54.581559-05	nndz-WkNPd3hMM3hndz09	4511	t	\N	9	6	60.00		2025-06-24 19:48:54.581559-05	0	0	0	0.00	13511
328059	\N	Harold	Martin	4588	4292	2025-06-24 19:48:54.581559-05	nndz-WkNPd3hMYjZnUT09	4511	t	10.90	15	9	62.50		2025-06-24 19:48:54.581559-05	0	0	0	0.00	13511
328060	\N	Ryan	Mullaney III	4588	4292	2025-06-24 19:48:54.581559-05	nndz-WkNPd3hMMzZnQT09	4511	t	\N	16	11	59.30		2025-06-24 19:48:54.581559-05	0	0	0	0.00	13511
328061	\N	Greg	Snow	4588	4292	2025-06-24 19:48:54.581559-05	nndz-WkNPd3liLzloQT09	4511	t	18.70	7	9	43.80		2025-06-24 19:48:54.581559-05	0	0	0	0.00	13511
328062	\N	TJ	Sobczak	4588	4292	2025-06-24 19:48:54.581559-05	nndz-WkNHeHhMbjloUT09	4511	t	28.40	5	7	41.70		2025-06-24 19:48:54.581559-05	0	0	0	0.00	13511
328063	\N	Pat	Usher	4588	4292	2025-06-24 19:48:54.581559-05	nndz-WkNPd3hMMzZoZz09	4511	t	18.80	8	9	47.10		2025-06-24 19:48:54.581559-05	0	0	0	0.00	13511
328064	\N	Peter	Roeser	4593	4292	2025-06-24 19:48:54.581559-05	nndz-WkNPd3hMdjRnUT09	4511	t	15.20	9	5	64.30	C	2025-06-24 19:48:54.581559-05	0	0	0	0.00	13552
328065	\N	Scott	Bondurant	4593	4292	2025-06-24 19:48:54.581559-05	nndz-WkNPd3hMMzdndz09	4511	t	\N	7	9	43.80		2025-06-24 19:48:54.581559-05	0	0	0	0.00	13552
328066	\N	Drew	Campbell	4593	4292	2025-06-24 19:48:54.581559-05	nndz-WkNPd3hMdjRoUT09	4511	t	\N	4	5	44.40		2025-06-24 19:48:54.581559-05	0	0	0	0.00	13552
328067	\N	Gordie	Campbell	4593	4292	2025-06-24 19:48:54.581559-05	nndz-WkNPd3hyL3hnZz09	4511	t	19.50	5	11	31.20		2025-06-24 19:48:54.581559-05	0	0	0	0.00	13552
328068	\N	Kevan	Comstock	4593	4292	2025-06-24 19:48:54.581559-05	nndz-WkNPd3hMajdoZz09	4511	t	23.20	0	0	0.00		2025-06-24 19:48:54.581559-05	0	0	0	0.00	13552
328069	\N	John	Hart	4593	4292	2025-06-24 19:48:54.581559-05	nndz-WkNPd3hMdjVnZz09	4511	t	29.20	5	7	41.70		2025-06-24 19:48:54.581559-05	0	0	0	0.00	13552
328070	\N	Jake	Henry	4593	4292	2025-06-24 19:48:54.581559-05	nndz-WkNPd3hMajRodz09	4511	t	27.10	2	5	28.60		2025-06-24 19:48:54.581559-05	0	0	0	0.00	13552
328071	\N	Patrick	Kalotis	4593	4292	2025-06-24 19:48:54.581559-05	nndz-WkNHN3diYjlnZz09	4511	t	28.20	10	10	50.00		2025-06-24 19:48:54.581559-05	0	0	0	0.00	13552
328072	\N	Peter	Martay	4593	4292	2025-06-24 19:48:54.581559-05	nndz-WkNDNnlMbjZndz09	4511	t	30.30	4	13	23.50		2025-06-24 19:48:54.581559-05	0	0	0	0.00	13552
328073	\N	Ford	Martin	4593	4292	2025-06-24 19:48:54.581559-05	nndz-WkNDNnhyYjVndz09	4511	t	20.30	6	10	37.50		2025-06-24 19:48:54.581559-05	0	0	0	0.00	13552
328074	\N	Andy	McNerney	4593	4292	2025-06-24 19:48:54.581559-05	nndz-WkNPd3g3NzdnZz09	4511	t	18.10	10	4	71.40		2025-06-24 19:48:54.581559-05	0	0	0	0.00	13552
328075	\N	Thomas	Merriman	4593	4292	2025-06-24 19:48:54.581559-05	nndz-WkNPd3hyejVnZz09	4511	t	21.40	11	11	50.00		2025-06-24 19:48:54.581559-05	0	0	0	0.00	13552
328076	\N	Matthew	Warner	4593	4292	2025-06-24 19:48:54.581559-05	nndz-WkNPd3hMejhnZz09	4511	t	\N	13	9	59.10		2025-06-24 19:48:54.581559-05	0	0	0	0.00	13552
328077	\N	Chris	Longeway	4600	4292	2025-06-24 19:48:54.581559-05	nndz-WkNPd3g3Nzlndz09	4511	t	29.50	4	8	33.30	C	2025-06-24 19:48:54.581559-05	0	0	0	0.00	13620
328078	\N	JD	Mynhier	4600	4292	2025-06-24 19:48:54.581559-05	nndz-WkNHeHhiejdoUT09	4511	t	15.20	11	7	61.10	CC	2025-06-24 19:48:54.581559-05	0	0	0	0.00	13620
328079	\N	Gui	Axus	4600	4292	2025-06-24 19:48:54.581559-05	nndz-WkNHeHdyLytnZz09	4511	t	20.20	6	8	42.90		2025-06-24 19:48:54.581559-05	0	0	0	0.00	13620
328080	\N	Nick	Cromydas	4600	4292	2025-06-24 19:48:54.581559-05	nndz-WkNPd3hMendnQT09	4511	t	\N	7	5	58.30		2025-06-24 19:48:54.581559-05	0	0	0	0.00	13620
328081	\N	Tony	Fiordaliso	4600	4292	2025-06-24 19:48:54.581559-05	nndz-WkNPd3hMZjRqUT09	4511	t	32.30	8	17	32.00		2025-06-24 19:48:54.581559-05	0	0	0	0.00	13620
328082	\N	Scott	Green	4600	4292	2025-06-24 19:48:54.581559-05	nndz-WkNPd3hMMzZnZz09	4511	t	\N	16	14	53.30		2025-06-24 19:48:54.581559-05	0	0	0	0.00	13620
328083	\N	Rick	Hoskins	4600	4292	2025-06-24 19:48:54.581559-05	nndz-WkNPd3g3NzlnUT09	4511	t	23.10	7	7	50.00		2025-06-24 19:48:54.581559-05	0	0	0	0.00	13620
328084	\N	Ryan	Long	4600	4292	2025-06-24 19:48:54.581559-05	nndz-WkNPd3g3Nzdndz09	4511	t	25.20	4	14	22.20		2025-06-24 19:48:54.581559-05	0	0	0	0.00	13620
328085	\N	Sam	O'Malley	4600	4292	2025-06-24 19:48:54.581559-05	nndz-WkNPd3hMcjRoQT09	4511	t	\N	0	0	0.00		2025-06-24 19:48:54.581559-05	0	0	0	0.00	13620
328086	\N	Andrew	Price	4600	4292	2025-06-24 19:48:54.581559-05	nndz-WkNPd3g3NzhnQT09	4511	t	28.10	1	10	9.10		2025-06-24 19:48:54.581559-05	0	0	0	0.00	13620
328087	\N	Tom	Rowland	4600	4292	2025-06-24 19:48:54.581559-05	nndz-WkNPd3hMMzVoUT09	4511	t	\N	12	9	57.10		2025-06-24 19:48:54.581559-05	0	0	0	0.00	13620
328088	\N	Evan	Salmela	4600	4292	2025-06-24 19:48:54.581559-05	nndz-WkNHeHdyYjRodz09	4511	t	18.20	7	9	43.80		2025-06-24 19:48:54.581559-05	0	0	0	0.00	13620
328089	\N	Douglas	Freedman	4601	4292	2025-06-24 19:48:54.581559-05	nndz-WkNPd3hMai9odz09	4511	t	14.70	6	10	37.50	C	2025-06-24 19:48:54.581559-05	0	0	0	0.00	13635
328090	\N	Andrew	Becker	4601	4292	2025-06-24 19:48:54.581559-05	nndz-WkNPd3hMajZnQT09	4511	t	24.50	2	11	15.40		2025-06-24 19:48:54.581559-05	0	0	0	0.00	13635
328091	\N	Chris	Engelman	4601	4292	2025-06-24 19:48:54.581559-05	nndz-WkNPd3hMajhqUT09	4511	t	25.40	7	12	36.80		2025-06-24 19:48:54.581559-05	0	0	0	0.00	13635
328092	\N	Andy	Farbman	4601	4292	2025-06-24 19:48:54.581559-05	nndz-WkNPd3hMajZqUT09	4511	t	22.10	8	14	36.40		2025-06-24 19:48:54.581559-05	0	0	0	0.00	13635
328093	\N	Bryan	Fox	4601	4292	2025-06-24 19:48:54.581559-05	nndz-WlNlNHhMYjZoUT09	4511	t	24.90	3	11	21.40		2025-06-24 19:48:54.581559-05	0	0	0	0.00	13635
328094	\N	Bill	Friend	4601	4292	2025-06-24 19:48:54.581559-05	nndz-WkNPd3g3YjVqQT09	4511	t	26.30	10	18	35.70		2025-06-24 19:48:54.581559-05	0	0	0	0.00	13635
328095	\N	Matt	Harris	4601	4292	2025-06-24 19:48:54.581559-05	nndz-WkNPd3hMajZoZz09	4511	t	12.20	16	19	45.70		2025-06-24 19:48:54.581559-05	0	0	0	0.00	13635
328096	\N	Miles	J Harris	4601	4292	2025-06-24 19:48:54.581559-05	nndz-WkNPd3hManhoQT09	4511	t	31.10	1	8	11.10		2025-06-24 19:48:54.581559-05	0	0	0	0.00	13635
328097	\N	Jeff	Kaplan	4601	4292	2025-06-24 19:48:54.581559-05	nndz-WkNPd3hMaitoZz09	4511	t	34.10	2	10	16.70		2025-06-24 19:48:54.581559-05	0	0	0	0.00	13635
328098	\N	Charlie	Phillips	4601	4292	2025-06-24 19:48:54.581559-05	nndz-WkNPd3hMcjRqUT09	4511	t	15.90	3	11	21.40		2025-06-24 19:48:54.581559-05	0	0	0	0.00	13635
328099	\N	David	Richter	4601	4292	2025-06-24 19:48:54.581559-05	nndz-WkNPd3hMbjRnZz09	4511	t	32.10	0	1	0.00		2025-06-24 19:48:54.581559-05	0	0	0	0.00	13635
328100	\N	Jeff	Seifman	4601	4292	2025-06-24 19:48:54.581559-05	nndz-WkNPd3hManhnUT09	4511	t	35.00	3	6	33.30		2025-06-24 19:48:54.581559-05	0	0	0	0.00	13635
328101	\N	Danny	Tornea	4601	4292	2025-06-24 19:48:54.581559-05	nndz-WkMrK3hiei9nQT09	4511	t	20.20	3	5	37.50		2025-06-24 19:48:54.581559-05	0	0	0	0.00	13635
328102	\N	Luke	Clarkson	4602	4292	2025-06-24 19:48:54.581559-05	nndz-WkNPd3hMYjRqUT09	4511	t	25.90	5	8	38.50	C	2025-06-24 19:48:54.581559-05	0	0	0	0.00	13646
328103	\N	Dan	Adajian	4602	4292	2025-06-24 19:48:54.581559-05	nndz-WkNPd3hMYnhoQT09	4511	t	\N	14	7	66.70		2025-06-24 19:48:54.581559-05	0	0	0	0.00	13646
328104	\N	Eric	C Anderson	4602	4292	2025-06-24 19:48:54.581559-05	nndz-WkNPd3hMbi9nZz09	4511	t	27.20	5	8	38.50		2025-06-24 19:48:54.581559-05	0	0	0	0.00	13646
328105	\N	Jack	Bryant	4602	4292	2025-06-24 19:48:54.581559-05	nndz-WlNlN3dMM3dnZz09	4511	t	22.30	7	9	43.80		2025-06-24 19:48:54.581559-05	0	0	0	0.00	13646
328106	\N	Keegan	DeSilva	4602	4292	2025-06-24 19:48:54.581559-05	nndz-WkNHNXc3ajdodz09	4511	t	\N	14	4	77.80		2025-06-24 19:48:54.581559-05	0	0	0	0.00	13646
328107	\N	Josh	Graves	4602	4292	2025-06-24 19:48:54.581559-05	nndz-WlNlNnhibjVndz09	4511	t	13.10	8	10	44.40		2025-06-24 19:48:54.581559-05	0	0	0	0.00	13646
328108	\N	Michael	Hulseman	4602	4292	2025-06-24 19:48:54.581559-05	nndz-WkNDNnhydjdqQT09	4511	t	17.40	11	9	55.00		2025-06-24 19:48:54.581559-05	0	0	0	0.00	13646
328109	\N	Luke	Johnson	4602	4292	2025-06-24 19:48:54.581559-05	nndz-WkNPd3hyNzVoZz09	4511	t	19.10	4	3	57.10		2025-06-24 19:48:54.581559-05	0	0	0	0.00	13646
328110	\N	Chris	Lashmet	4602	4292	2025-06-24 19:48:54.581559-05	nndz-WkNPd3hMMzdoQT09	4511	t	18.20	5	8	38.50		2025-06-24 19:48:54.581559-05	0	0	0	0.00	13646
328111	\N	Sebastian	McGreevey	4602	4292	2025-06-24 19:48:54.581559-05	nndz-WkNPd3hMYjRnZz09	4511	t	28.90	6	5	54.50		2025-06-24 19:48:54.581559-05	0	0	0	0.00	13646
328112	\N	Pete	Stellas	4602	4292	2025-06-24 19:48:54.581559-05	nndz-WkNPd3hMajlqUT09	4511	t	27.60	1	5	16.70		2025-06-24 19:48:54.581559-05	0	0	0	0.00	13646
328113	\N	Tommy	Sullivan	4602	4292	2025-06-24 19:48:54.581559-05	nndz-WkM2L3hidi9oUT09	4511	t	16.30	22	9	71.00		2025-06-24 19:48:54.581559-05	0	0	0	0.00	13646
328114	\N	Michael	Phillips	4611	4292	2025-06-24 19:48:54.581559-05	nndz-WkNPd3hMditqUT09	4511	t	15.30	12	7	63.20	C	2025-06-24 19:48:54.581559-05	0	0	0	0.00	13735
328115	\N	Paul	Buckingham	4611	4292	2025-06-24 19:48:54.581559-05	nndz-WkNPd3hMditoUT09	4511	t	\N	2	2	50.00		2025-06-24 19:48:54.581559-05	0	0	0	0.00	13735
328116	\N	Connor	Casas	4611	4292	2025-06-24 19:48:54.581559-05	nndz-WkNDNnhyYjZoQT09	4511	t	15.60	15	7	68.20		2025-06-24 19:48:54.581559-05	0	0	0	0.00	13735
328117	\N	Will	Colmar	4611	4292	2025-06-24 19:48:54.581559-05	nndz-WkNPd3hMeitoZz09	4511	t	\N	14	6	70.00		2025-06-24 19:48:54.581559-05	0	0	0	0.00	13735
328118	\N	Jamie	Daul	4611	4292	2025-06-24 19:48:54.581559-05	nndz-WkNPd3g3LzZqQT09	4511	t	17.30	11	4	73.30		2025-06-24 19:48:54.581559-05	0	0	0	0.00	13735
328119	\N	Adam	LaVoy	4611	4292	2025-06-24 19:48:54.581559-05	nndz-WkNPd3hyai9qQT09	4511	t	29.50	5	7	41.70		2025-06-24 19:48:54.581559-05	0	0	0	0.00	13735
328120	\N	Karl	Morgan	4611	4292	2025-06-24 19:48:54.581559-05	nndz-WkNPd3hMeitnZz09	4511	t	16.20	9	6	60.00		2025-06-24 19:48:54.581559-05	0	0	0	0.00	13735
328121	\N	John	Patience	4611	4292	2025-06-24 19:48:54.581559-05	nndz-WkNPd3hMdjdoUT09	4511	t	29.50	3	6	33.30		2025-06-24 19:48:54.581559-05	0	0	0	0.00	13735
328122	\N	Patrick	Shields	4611	4292	2025-06-24 19:48:54.581559-05	nndz-WkNDd3lMbndoZz09	4511	t	24.00	5	3	62.50		2025-06-24 19:48:54.581559-05	0	0	0	0.00	13735
328123	\N	George	Sullivan	4611	4292	2025-06-24 19:48:54.581559-05	nndz-WkNDNnhyYnhqQT09	4511	t	17.80	18	10	64.30		2025-06-24 19:48:54.581559-05	0	0	0	0.00	13735
328124	\N	Harry	Sullivan	4611	4292	2025-06-24 19:48:54.581559-05	nndz-WkNPd3hMMzRqUT09	4511	t	\N	19	5	79.20		2025-06-24 19:48:54.581559-05	0	0	0	0.00	13735
328125	\N	Matt	Sullivan	4611	4292	2025-06-24 19:48:54.581559-05	nndz-WkNDNnhyYnhqUT09	4511	t	27.80	9	9	50.00		2025-06-24 19:48:54.581559-05	0	0	0	0.00	13735
328126	\N	Ryan	Sullivan	4611	4292	2025-06-24 19:48:54.581559-05	nndz-WkNHeHg3YjhqUT09	4511	t	30.70	6	10	37.50		2025-06-24 19:48:54.581559-05	0	0	0	0.00	13735
328127	\N	Matt	Swaim	4611	4292	2025-06-24 19:48:54.581559-05	nndz-WkNPd3g3YjVoUT09	4511	t	28.70	3	6	33.30		2025-06-24 19:48:54.581559-05	0	0	0	0.00	13735
328128	\N	Jeremy	Edelson	4612	4292	2025-06-24 19:48:54.581559-05	nndz-WkNPd3hMajdnUT09	4511	t	\N	7	10	41.20	C	2025-06-24 19:48:54.581559-05	0	0	0	0.00	13753
328129	\N	Chad	Eisenberg	4612	4292	2025-06-24 19:48:54.581559-05	nndz-WkNPd3hMajdqQT09	4511	t	18.30	6	7	46.20	CC	2025-06-24 19:48:54.581559-05	0	0	0	0.00	13753
328130	\N	Michael	Benson	4612	4292	2025-06-24 19:48:54.581559-05	nndz-WkNPd3g3LzVndz09	4511	t	16.10	11	7	61.10		2025-06-24 19:48:54.581559-05	0	0	0	0.00	13753
328131	\N	Michael	Brual	4612	4292	2025-06-24 19:48:54.581559-05	nndz-WkNPd3hMdjhnZz09	4511	t	19.10	5	9	35.70		2025-06-24 19:48:54.581559-05	0	0	0	0.00	13753
328132	\N	Ed	Clamage	4612	4292	2025-06-24 19:48:54.581559-05	nndz-WlNlL3hybi9odz09	4511	t	\N	0	0	0.00		2025-06-24 19:48:54.581559-05	0	0	0	0.00	13753
328133	\N	Brent	Damico	4612	4292	2025-06-24 19:48:54.581559-05	nndz-WkM2d3dyYnhodz09	4511	t	19.10	15	6	71.40		2025-06-24 19:48:54.581559-05	0	0	0	0.00	13753
328134	\N	Ryan	Daube	4612	4292	2025-06-24 19:48:54.581559-05	nndz-WkNPd3hMajZodz09	4511	t	27.10	0	3	0.00		2025-06-24 19:48:54.581559-05	0	0	0	0.00	13753
328135	\N	Derek	Fish	4612	4292	2025-06-24 19:48:54.581559-05	nndz-WkNPd3hMbi9ndz09	4511	t	18.30	7	12	36.80		2025-06-24 19:48:54.581559-05	0	0	0	0.00	13753
328136	\N	Vineeth	Gossain	4612	4292	2025-06-24 19:48:54.581559-05	nndz-WkNPd3hMM3hqUT09	4511	t	\N	7	7	50.00		2025-06-24 19:48:54.581559-05	0	0	0	0.00	13753
328137	\N	Jacob	Groce	4612	4292	2025-06-24 19:48:54.581559-05	nndz-WkMreHdiN3doUT09	4511	t	13.80	11	19	36.70		2025-06-24 19:48:54.581559-05	0	0	0	0.00	13753
328138	\N	Mark	Harris	4612	4292	2025-06-24 19:48:54.581559-05	nndz-WkNPd3g3LzVnZz09	4511	t	20.70	12	11	52.20		2025-06-24 19:48:54.581559-05	0	0	0	0.00	13753
328139	\N	Rich	Learner	4612	4292	2025-06-24 19:48:54.581559-05	nndz-WkNPd3hMajdnZz09	4511	t	20.00	5	4	55.60		2025-06-24 19:48:54.581559-05	0	0	0	0.00	13753
328140	\N	Charles	Leger	4612	4292	2025-06-24 19:48:54.581559-05	nndz-WkNPd3hMenhoQT09	4511	t	11.10	0	5	0.00		2025-06-24 19:48:54.581559-05	0	0	0	0.00	13753
328141	\N	Josh	Leighton	4612	4292	2025-06-24 19:48:54.581559-05	nndz-WkNDOHhML3hnUT09	4511	t	19.60	7	5	58.30		2025-06-24 19:48:54.581559-05	0	0	0	0.00	13753
328142	\N	Scott	Levy	4612	4292	2025-06-24 19:48:54.581559-05	nndz-WkNHNXg3MzRodz09	4511	t	29.10	7	10	41.20		2025-06-24 19:48:54.581559-05	0	0	0	0.00	13753
328143	\N	Justin	Lewis	4612	4292	2025-06-24 19:48:54.581559-05	nndz-WkNPd3hMaitnZz09	4511	t	19.20	0	0	0.00		2025-06-24 19:48:54.581559-05	0	0	0	0.00	13753
328144	\N	Ben	Woldenberg	4612	4292	2025-06-24 19:48:54.581559-05	nndz-WkNPd3hMai9qUT09	4511	t	13.10	7	7	50.00		2025-06-24 19:48:54.581559-05	0	0	0	0.00	13753
328145	\N	John	Noell	4630	4292	2025-06-24 19:48:54.581559-05	nndz-WkNPd3hMbjdodz09	4511	t	12.90	12	8	60.00	C	2025-06-24 19:48:54.581559-05	0	0	0	0.00	13833
328146	\N	Anthony	Appleyard	4630	4292	2025-06-24 19:48:54.581559-05	nndz-WkNDd3lMajdodz09	4511	t	\N	18	17	51.40		2025-06-24 19:48:54.581559-05	0	0	0	0.00	13833
328147	\N	Michael	Franco	4630	4292	2025-06-24 19:48:54.581559-05	nndz-WkNPd3hMcjZoZz09	4511	t	\N	16	20	44.40		2025-06-24 19:48:54.581559-05	0	0	0	0.00	13833
328148	\N	Timothy	Kessler	4630	4292	2025-06-24 19:48:54.581559-05	nndz-WkNPd3hMajhndz09	4511	t	\N	11	4	73.30		2025-06-24 19:48:54.581559-05	0	0	0	0.00	13833
328149	\N	Vince	Lombardi	4630	4292	2025-06-24 19:48:54.581559-05	nndz-WkNPd3hMci9odz09	4511	t	15.10	9	3	75.00		2025-06-24 19:48:54.581559-05	0	0	0	0.00	13833
328150	\N	Sam	Meyer	4630	4292	2025-06-24 19:48:54.581559-05	nndz-WkNHeHc3Yi9oZz09	4511	t	19.00	11	12	47.80		2025-06-24 19:48:54.581559-05	0	0	0	0.00	13833
328151	\N	Chris	Pirrera	4630	4292	2025-06-24 19:48:54.581559-05	nndz-WkNPd3licitodz09	4511	t	24.30	8	5	61.50		2025-06-24 19:48:54.581559-05	0	0	0	0.00	13833
328152	\N	Mark	Schaefer	4630	4292	2025-06-24 19:48:54.581559-05	nndz-WkNPd3hMM3doUT09	4511	t	\N	14	16	46.70		2025-06-24 19:48:54.581559-05	0	0	0	0.00	13833
328153	\N	Ross	Sprovieri	4630	4292	2025-06-24 19:48:54.581559-05	nndz-WkNPd3hMajhnUT09	4511	t	23.30	7	8	46.70		2025-06-24 19:48:54.581559-05	0	0	0	0.00	13833
328154	\N	Rob	Young	4630	4292	2025-06-24 19:48:54.581559-05	nndz-WkNPd3g3MzRqQT09	4511	t	18.20	18	10	64.30		2025-06-24 19:48:54.581559-05	0	0	0	0.00	13833
328155	\N	Luke	Marker	4631	4292	2025-06-24 19:48:54.581559-05	nndz-WkNPd3g3ejVndz09	4511	t	13.40	9	8	52.90	C	2025-06-24 19:48:54.581559-05	0	0	0	0.00	13846
328156	\N	Kirk	Baldwin	4631	4292	2025-06-24 19:48:54.581559-05	nndz-WkNPd3hMYjVoZz09	4511	t	28.60	8	10	44.40		2025-06-24 19:48:54.581559-05	0	0	0	0.00	13846
328157	\N	Alex	Cotard	4631	4292	2025-06-24 19:48:54.581559-05	nndz-WkM2L3dMbi9oZz09	4511	t	\N	13	8	61.90		2025-06-24 19:48:54.581559-05	0	0	0	0.00	13846
328158	\N	Christian	Duchnak	4631	4292	2025-06-24 19:48:54.581559-05	nndz-WkM2K3c3cnhoUT09	4511	t	\N	18	4	81.80		2025-06-24 19:48:54.581559-05	0	0	0	0.00	13846
328159	\N	David	J Fox	4631	4292	2025-06-24 19:48:54.581559-05	nndz-WkNPd3g3Yi9nQT09	4511	t	15.30	12	6	66.70		2025-06-24 19:48:54.581559-05	0	0	0	0.00	13846
328160	\N	Bob	Herber	4631	4292	2025-06-24 19:48:54.581559-05	nndz-WkNPd3hMbjhndz09	4511	t	22.80	8	10	44.40		2025-06-24 19:48:54.581559-05	0	0	0	0.00	13846
328161	\N	John	Pak	4631	4292	2025-06-24 19:48:54.581559-05	nndz-WkNPd3hMYitoQT09	4511	t	22.60	1	0	100.00		2025-06-24 19:48:54.581559-05	0	0	0	0.00	13846
328162	\N	Mason	Phelps	4631	4292	2025-06-24 19:48:54.581559-05	nndz-WkNDd3lMZndodz09	4511	t	15.60	14	5	73.70		2025-06-24 19:48:54.581559-05	0	0	0	0.00	13846
328163	\N	Reid	Snyder	4631	4292	2025-06-24 19:48:54.581559-05	nndz-WkNHN3dMNzVqQT09	4511	t	19.20	15	5	75.00		2025-06-24 19:48:54.581559-05	0	0	0	0.00	13846
328164	\N	Drake	Weyermuller	4631	4292	2025-06-24 19:48:54.581559-05	nndz-WkNPd3hMZjdoQT09	4511	t	\N	14	7	66.70		2025-06-24 19:48:54.581559-05	0	0	0	0.00	13846
328165	\N	Chase	Berlinghof	4635	4292	2025-06-24 19:48:54.581559-05	nndz-WkNPd3g3ZjVnZz09	4511	t	20.60	13	6	68.40	C	2025-06-24 19:48:54.581559-05	0	0	0	0.00	13876
328166	\N	Max	Byrne	4635	4292	2025-06-24 19:48:54.581559-05	nndz-WkNDOXdiajVnQT09	4511	t	22.00	7	9	43.80		2025-06-24 19:48:54.581559-05	0	0	0	0.00	13876
328167	\N	Robert	Matteson	4635	4292	2025-06-24 19:48:54.581559-05	nndz-WkNPd3g3ci9qUT09	4511	t	25.20	8	2	80.00		2025-06-24 19:48:54.581559-05	0	0	0	0.00	13876
328168	\N	Paget	Neave	4635	4292	2025-06-24 19:48:54.581559-05	nndz-WkNPd3hMMzlnZz09	4511	t	\N	17	16	51.50		2025-06-24 19:48:54.581559-05	0	0	0	0.00	13876
328169	\N	Keegan	O'Brien	4635	4292	2025-06-24 19:48:54.581559-05	nndz-WkNHeHhMZjRodz09	4511	t	17.80	18	10	64.30		2025-06-24 19:48:54.581559-05	0	0	0	0.00	13876
328170	\N	Peter	Slaven	4635	4292	2025-06-24 19:48:54.581559-05	nndz-WkNPd3hMcjZndz09	4511	t	13.50	10	5	66.70		2025-06-24 19:48:54.581559-05	0	0	0	0.00	13876
328171	\N	Robert	Stineman	4635	4292	2025-06-24 19:48:54.581559-05	nndz-WkNPd3hMMzRnQT09	4511	t	\N	13	5	72.20		2025-06-24 19:48:54.581559-05	0	0	0	0.00	13876
328172	\N	Matt	Ward	4635	4292	2025-06-24 19:48:54.581559-05	nndz-WkNPd3hMcjRnZz09	4511	t	13.40	11	4	73.30		2025-06-24 19:48:54.581559-05	0	0	0	0.00	13876
328173	\N	Riley	Wilton	4635	4292	2025-06-24 19:48:54.581559-05	nndz-WkM2L3dMYjRnZz09	4511	t	21.50	13	6	68.40		2025-06-24 19:48:54.581559-05	0	0	0	0.00	13876
328174	\N	Billy	Wright	4635	4292	2025-06-24 19:48:54.581559-05	nndz-WkNPd3lidjlqUT09	4511	t	19.90	9	5	64.30		2025-06-24 19:48:54.581559-05	0	0	0	0.00	13876
328175	\N	Stephen	Larko	4646	4292	2025-06-24 19:48:54.581559-05	nndz-WkNPd3hMYjZqQT09	4511	t	12.40	20	19	51.30	C	2025-06-24 19:48:54.581559-05	0	0	0	0.00	14084
328176	\N	Ethan	Bershtein	4646	4292	2025-06-24 19:48:54.581559-05	nndz-WlNlN3liZitqUT09	4511	t	\N	7	4	63.60		2025-06-24 19:48:54.581559-05	0	0	0	0.00	14084
328177	\N	Bryan	Bertola	4646	4292	2025-06-24 19:48:54.581559-05	nndz-WkM2OHg3citqQT09	4511	t	16.20	16	19	45.70		2025-06-24 19:48:54.581559-05	0	0	0	0.00	14084
328178	\N	Casey	Conaghan	4646	4292	2025-06-24 19:48:54.581559-05	nndz-WkNPd3hMcnhnQT09	4511	t	22.70	3	7	30.00		2025-06-24 19:48:54.581559-05	0	0	0	0.00	14084
328179	\N	Todd	Grossnickle	4646	4292	2025-06-24 19:48:54.581559-05	nndz-WkNDNnhyZjRoUT09	4511	t	25.30	5	6	45.50		2025-06-24 19:48:54.581559-05	0	0	0	0.00	14084
328180	\N	Michael	Gruber	4646	4292	2025-06-24 19:48:54.581559-05	nndz-WkNPd3hMZjZnQT09	4511	t	18.20	25	5	83.30		2025-06-24 19:48:54.581559-05	0	0	0	0.00	14084
328181	\N	Kevin	Lyons	4646	4292	2025-06-24 19:48:54.581559-05	nndz-WkNPd3g3N3hodz09	4511	t	21.30	7	2	77.80		2025-06-24 19:48:54.581559-05	0	0	0	0.00	14084
328182	\N	Bryant	McWhorter	4646	4292	2025-06-24 19:48:54.581559-05	nndz-WkNPd3hMZjRndz09	4511	t	15.50	14	11	56.00		2025-06-24 19:48:54.581559-05	0	0	0	0.00	14084
328183	\N	Dane	Olsen	4646	4292	2025-06-24 19:48:54.581559-05	nndz-WkMrK3dyajlodz09	4511	t	21.30	10	6	62.50		2025-06-24 19:48:54.581559-05	0	0	0	0.00	14084
328184	\N	Addom	Powell	4646	4292	2025-06-24 19:48:54.581559-05	nndz-WkNPd3hMbjloZz09	4511	t	18.80	14	9	60.90		2025-06-24 19:48:54.581559-05	0	0	0	0.00	14084
328185	\N	Tony	Soruco	4646	4292	2025-06-24 19:48:54.581559-05	nndz-WkM2OHlianhnUT09	4511	t	15.90	8	8	50.00		2025-06-24 19:48:54.581559-05	0	0	0	0.00	14084
328186	\N	Peter	Stellas Jr	4646	4292	2025-06-24 19:48:54.581559-05	nndz-WkNDNnhydjVndz09	4511	t	\N	15	9	62.50		2025-06-24 19:48:54.581559-05	0	0	0	0.00	14084
328187	\N	Brian	Woodruff	4649	4292	2025-06-24 19:48:54.581559-05	nndz-WkNPd3g3LzRnZz09	4511	t	23.40	17	13	56.70	C	2025-06-24 19:48:54.581559-05	0	0	0	0.00	14124
328188	\N	Paul	Carollo	4649	4292	2025-06-24 19:48:54.581559-05	nndz-WkNPd3hMcjhoUT09	4511	t	29.40	6	5	54.50		2025-06-24 19:48:54.581559-05	0	0	0	0.00	14124
328189	\N	PJ	Carollo	4649	4292	2025-06-24 19:48:54.581559-05	nndz-WkNDd3lMLzlnQT09	4511	t	17.40	8	8	50.00		2025-06-24 19:48:54.581559-05	0	0	0	0.00	14124
328190	\N	Greg	Cran	4649	4292	2025-06-24 19:48:54.581559-05	nndz-WkNDd3liYjRnUT09	4511	t	25.70	3	13	18.80		2025-06-24 19:48:54.581559-05	0	0	0	0.00	14124
328191	\N	Dan	Daehler	4649	4292	2025-06-24 19:48:54.581559-05	nndz-WkNPd3hMdjhnUT09	4511	t	14.70	9	3	75.00		2025-06-24 19:48:54.581559-05	0	0	0	0.00	14124
328192	\N	Terry	Dee	4649	4292	2025-06-24 19:48:54.581559-05	nndz-WkNPd3hMcjhnUT09	4511	t	25.50	14	9	60.90		2025-06-24 19:48:54.581559-05	0	0	0	0.00	14124
328193	\N	Scott	Gottman	4649	4292	2025-06-24 19:48:54.581559-05	nndz-WkNPd3hMcitodz09	4511	t	13.80	17	6	73.90		2025-06-24 19:48:54.581559-05	0	0	0	0.00	14124
328194	\N	Bill	Henricks	4649	4292	2025-06-24 19:48:54.581559-05	nndz-WkNPd3hMbnhnZz09	4511	t	29.30	4	9	30.80		2025-06-24 19:48:54.581559-05	0	0	0	0.00	14124
328195	\N	Mark	Johnson	4649	4292	2025-06-24 19:48:54.581559-05	nndz-WkNPd3hMcnhodz09	4511	t	\N	9	2	81.80		2025-06-24 19:48:54.581559-05	0	0	0	0.00	14124
328196	\N	Blair	Lockhart	4649	4292	2025-06-24 19:48:54.581559-05	nndz-WkNPd3hMcnhqQT09	4511	t	29.10	2	5	28.60		2025-06-24 19:48:54.581559-05	0	0	0	0.00	14124
328197	\N	Mike	Milliman	4649	4292	2025-06-24 19:48:54.581559-05	nndz-WkNPd3g3LzloQT09	4511	t	26.40	17	11	60.70		2025-06-24 19:48:54.581559-05	0	0	0	0.00	14124
328198	\N	Trey	Minter	4649	4292	2025-06-24 19:48:54.581559-05	nndz-WkNPd3hMcjRnUT09	4511	t	10.00	14	10	58.30		2025-06-24 19:48:54.581559-05	0	0	0	0.00	14124
328199	\N	Mike	Sims	4649	4292	2025-06-24 19:48:54.581559-05	nndz-WkNDNnhyYjVnQT09	4511	t	\N	23	10	69.70		2025-06-24 19:48:54.581559-05	0	0	0	0.00	14124
328200	\N	Jason	Stanislaw	4649	4292	2025-06-24 19:48:54.581559-05	nndz-WkNPd3hMcndodz09	4511	t	24.20	7	16	30.40		2025-06-24 19:48:54.581559-05	0	0	0	0.00	14124
328201	\N	Ryan	Vahey	4649	4292	2025-06-24 19:48:54.581559-05	nndz-WkNPd3hMcjRoUT09	4511	t	16.00	9	5	64.30		2025-06-24 19:48:54.581559-05	0	0	0	0.00	14124
328202	\N	Tony	Sherwood	4571	4306	2025-06-24 19:48:54.581559-05	nndz-WkNPd3hMbjdnQT09	4511	t	28.90	3	7	30.00	C	2025-06-24 19:48:54.581559-05	0	0	0	0.00	13358
328203	\N	Alan	Abramson	4571	4306	2025-06-24 19:48:54.581559-05	nndz-WkNPd3hMbnhqUT09	4511	t	21.80	7	5	58.30		2025-06-24 19:48:54.581559-05	0	0	0	0.00	13358
328204	\N	Adam	Berman	4571	4306	2025-06-24 19:48:54.581559-05	nndz-WkNPd3hMajhnZz09	4511	t	30.70	3	12	20.00		2025-06-24 19:48:54.581559-05	0	0	0	0.00	13358
328205	\N	Chris	Engelman	4571	4306	2025-06-24 19:48:54.581559-05	nndz-WkNPd3hMajhqUT09	4511	t	25.40	7	12	36.80		2025-06-24 19:48:54.581559-05	0	0	0	0.00	13358
328206	\N	Jeff	Feldman	4571	4306	2025-06-24 19:48:54.581559-05	nndz-WkNPd3hMandqQT09	4511	t	24.80	4	11	26.70		2025-06-24 19:48:54.581559-05	0	0	0	0.00	13358
328207	\N	Bob	Libman	4571	4306	2025-06-24 19:48:54.581559-05	nndz-WkNPd3hManhoZz09	4511	t	25.30	2	7	22.20		2025-06-24 19:48:54.581559-05	0	0	0	0.00	13358
328208	\N	Mike	Mazursky	4571	4306	2025-06-24 19:48:54.581559-05	nndz-WkNPd3hMYjZnZz09	4511	t	30.10	2	3	40.00		2025-06-24 19:48:54.581559-05	0	0	0	0.00	13358
328209	\N	David	Raab	4571	4306	2025-06-24 19:48:54.581559-05	nndz-WkNPd3hMdnhoQT09	4511	t	36.10	2	14	12.50		2025-06-24 19:48:54.581559-05	0	0	0	0.00	13358
328210	\N	Stephen	Rudman	4571	4306	2025-06-24 19:48:54.581559-05	nndz-WkNPd3hMajhnQT09	4511	t	26.70	3	13	18.80		2025-06-24 19:48:54.581559-05	0	0	0	0.00	13358
328211	\N	Mike	Zucker	4571	4306	2025-06-24 19:48:54.581559-05	nndz-WkNPd3hMditqQT09	4511	t	23.70	4	9	30.80		2025-06-24 19:48:54.581559-05	0	0	0	0.00	13358
328212	\N	Nate	Hewitt	4586	4306	2025-06-24 19:48:54.581559-05	nndz-WkNDd3lMei9qQT09	4511	t	20.80	11	20	35.50	C	2025-06-24 19:48:54.581559-05	0	0	0	0.00	13500
328213	\N	Dan	Adajian	4586	4306	2025-06-24 19:48:54.581559-05	nndz-WkNPd3hMYnhoQT09	4511	t	\N	14	7	66.70		2025-06-24 19:48:54.581559-05	0	0	0	0.00	13500
328214	\N	rishi	awatramani	4586	4306	2025-06-24 19:48:54.581559-05	nndz-WkNPd3liYjZqUT09	4511	t	33.90	5	21	19.20		2025-06-24 19:48:54.581559-05	0	0	0	0.00	13500
328215	\N	Mitch	Dudek	4586	4306	2025-06-24 19:48:54.581559-05	nndz-WkNPd3g3NzlnZz09	4511	t	32.40	4	7	36.40		2025-06-24 19:48:54.581559-05	0	0	0	0.00	13500
328216	\N	Josh	Graves	4586	4306	2025-06-24 19:48:54.581559-05	nndz-WlNlNnhibjVndz09	4511	t	13.10	8	10	44.40		2025-06-24 19:48:54.581559-05	0	0	0	0.00	13500
328217	\N	Connor	Greenwald	4586	4306	2025-06-24 19:48:54.581559-05	nndz-WlNlNnhiMy9oUT09	4511	t	35.20	1	8	11.10		2025-06-24 19:48:54.581559-05	0	0	0	0.00	13500
328218	\N	Graham	Hallen	4586	4306	2025-06-24 19:48:54.581559-05	nndz-WkNHeHdMai9qUT09	4511	t	29.50	13	10	56.50		2025-06-24 19:48:54.581559-05	0	0	0	0.00	13500
328219	\N	Kort	Koppmann	4586	4306	2025-06-24 19:48:54.581559-05	nndz-WkNPd3g3NzZnQT09	4511	t	27.70	16	14	53.30		2025-06-24 19:48:54.581559-05	0	0	0	0.00	13500
328220	\N	Dan	Lomer	4586	4306	2025-06-24 19:48:54.581559-05	nndz-WkNPd3g3bjhodz09	4511	t	34.60	7	11	38.90		2025-06-24 19:48:54.581559-05	0	0	0	0.00	13500
328221	\N	David	Lord	4586	4306	2025-06-24 19:48:54.581559-05	nndz-WkM2L3c3ajloUT09	4511	t	31.50	7	8	46.70		2025-06-24 19:48:54.581559-05	0	0	0	0.00	13500
328222	\N	LJ	Maloney	4586	4306	2025-06-24 19:48:54.581559-05	nndz-WkNDd3lMbjlnZz09	4511	t	25.60	7	12	36.80		2025-06-24 19:48:54.581559-05	0	0	0	0.00	13500
328223	\N	Chad	Morris	4586	4306	2025-06-24 19:48:54.581559-05	nndz-WkM2eHhMZjVoZz09	4511	t	27.80	5	14	26.30		2025-06-24 19:48:54.581559-05	0	0	0	0.00	13500
328224	\N	Steve	Toomey	4586	4306	2025-06-24 19:48:54.581559-05	nndz-WkNPd3hMdndoQT09	4511	t	25.60	0	3	0.00		2025-06-24 19:48:54.581559-05	0	0	0	0.00	13500
328225	\N	Evan	Graf	4586	4306	2025-06-24 19:48:54.581559-05	nndz-WlNlN3g3NzRoUT09	4511	t	24.00	15	3	83.30		2025-06-24 19:48:54.581559-05	0	0	0	0.00	13500
328226	\N	Mike	West	4590	4306	2025-06-24 19:48:54.581559-05	nndz-WkNPd3hMZjhodz09	4511	t	15.50	15	4	78.90	C	2025-06-24 19:48:54.581559-05	0	0	0	0.00	13523
328227	\N	Mark	Parry	4590	4306	2025-06-24 19:48:54.581559-05	nndz-WkNDNnhyYitoQT09	4511	t	23.80	10	7	58.80	CC	2025-06-24 19:48:54.581559-05	0	0	0	0.00	13523
328228	\N	Zane	Fulton	4590	4306	2025-06-24 19:48:54.581559-05	nndz-WkNPd3hMcitoUT09	4511	t	19.00	8	6	57.10		2025-06-24 19:48:54.581559-05	0	0	0	0.00	13523
328229	\N	Mike	Gayed	4590	4306	2025-06-24 19:48:54.581559-05	nndz-WkNPd3hMYjZodz09	4511	t	25.50	9	7	56.20		2025-06-24 19:48:54.581559-05	0	0	0	0.00	13523
328230	\N	John	Griffin	4590	4306	2025-06-24 19:48:54.581559-05	nndz-WkNPd3hMYjhqUT09	4511	t	17.60	12	3	80.00		2025-06-24 19:48:54.581559-05	0	0	0	0.00	13523
328231	\N	Timothy	Kessler	4590	4306	2025-06-24 19:48:54.581559-05	nndz-WkNPd3hMajhndz09	4511	t	\N	11	4	73.30		2025-06-24 19:48:54.581559-05	0	0	0	0.00	13523
328232	\N	Phil	A. Lorenz	4590	4306	2025-06-24 19:48:54.581559-05	nndz-WkNPd3hMbjRnUT09	4511	t	23.50	7	8	46.70		2025-06-24 19:48:54.581559-05	0	0	0	0.00	13523
328233	\N	Chris	Mason	4590	4306	2025-06-24 19:48:54.581559-05	nndz-WkNPd3hMcjVoQT09	4511	t	22.30	9	4	69.20		2025-06-24 19:48:54.581559-05	0	0	0	0.00	13523
328234	\N	Kevin	Shea	4590	4306	2025-06-24 19:48:54.581559-05	nndz-WkNPd3hMYjVnUT09	4511	t	22.10	9	8	52.90		2025-06-24 19:48:54.581559-05	0	0	0	0.00	13523
328235	\N	Jason	Stuck	4590	4306	2025-06-24 19:48:54.581559-05	nndz-WkNDNnlManhndz09	4511	t	24.60	9	8	52.90		2025-06-24 19:48:54.581559-05	0	0	0	0.00	13523
328236	\N	Dave	Williams	4590	4306	2025-06-24 19:48:54.581559-05	nndz-WkNDNnhydjZnQT09	4511	t	25.40	10	7	58.80		2025-06-24 19:48:54.581559-05	0	0	0	0.00	13523
328237	\N	Greg	Cran	4599	4306	2025-06-24 19:48:54.581559-05	nndz-WkNDd3liYjRnUT09	4511	t	25.70	3	13	18.80	C	2025-06-24 19:48:54.581559-05	0	0	0	0.00	13604
328238	\N	Brian	Woodruff	4599	4306	2025-06-24 19:48:54.581559-05	nndz-WkNPd3g3LzRnZz09	4511	t	23.40	17	13	56.70	CC	2025-06-24 19:48:54.581559-05	0	0	0	0.00	13604
328239	\N	Dan	Daehler	4599	4306	2025-06-24 19:48:54.581559-05	nndz-WkNPd3hMdjhnUT09	4511	t	14.70	9	3	75.00		2025-06-24 19:48:54.581559-05	0	0	0	0.00	13604
328240	\N	Terry	Dee	4599	4306	2025-06-24 19:48:54.581559-05	nndz-WkNPd3hMcjhnUT09	4511	t	25.50	14	9	60.90		2025-06-24 19:48:54.581559-05	0	0	0	0.00	13604
328241	\N	Chris	Falls	4599	4306	2025-06-24 19:48:54.581559-05	nndz-WkNPd3hMbitqUT09	4511	t	18.50	11	12	47.80		2025-06-24 19:48:54.581559-05	0	0	0	0.00	13604
328242	\N	Bob	Geldermann	4599	4306	2025-06-24 19:48:54.581559-05	nndz-WkNPd3hMbjdqUT09	4511	t	25.60	4	5	44.40		2025-06-24 19:48:54.581559-05	0	0	0	0.00	13604
328243	\N	Dan	Kearny	4599	4306	2025-06-24 19:48:54.581559-05	nndz-WkNPd3g3LzRoZz09	4511	t	24.80	4	5	44.40		2025-06-24 19:48:54.581559-05	0	0	0	0.00	13604
328244	\N	Bill	Lambropoulos	4599	4306	2025-06-24 19:48:54.581559-05	nndz-WkNPd3hMbjZnQT09	4511	t	28.30	4	7	36.40		2025-06-24 19:48:54.581559-05	0	0	0	0.00	13604
328245	\N	Mike	Milliman	4599	4306	2025-06-24 19:48:54.581559-05	nndz-WkNPd3g3LzloQT09	4511	t	26.40	17	11	60.70		2025-06-24 19:48:54.581559-05	0	0	0	0.00	13604
328246	\N	Matt	Mulliken	4599	4306	2025-06-24 19:48:54.581559-05	nndz-WkNPd3hMdjdqUT09	4511	t	28.80	9	8	52.90		2025-06-24 19:48:54.581559-05	0	0	0	0.00	13604
328247	\N	Connor	Peckham	4599	4306	2025-06-24 19:48:54.581559-05	nndz-WkNPd3hMajRoQT09	4511	t	27.30	4	11	26.70		2025-06-24 19:48:54.581559-05	0	0	0	0.00	13604
328248	\N	Mike	Sims	4599	4306	2025-06-24 19:48:54.581559-05	nndz-WkNDNnhyYjVnQT09	4511	t	\N	23	10	69.70		2025-06-24 19:48:54.581559-05	0	0	0	0.00	13604
328249	\N	Brad	T Wilson	4610	4325	2025-06-24 19:48:54.581559-05	nndz-WkNPd3g3ejlndz09	4511	t	26.20	7	7	50.00	C	2025-06-24 19:48:54.581559-05	0	0	0	0.00	\N
328250	\N	Peter	Bourke	4610	4325	2025-06-24 19:48:54.581559-05	nndz-WkNPd3hMdjdqQT09	4511	t	25.30	0	2	0.00		2025-06-24 19:48:54.581559-05	0	0	0	0.00	\N
328251	\N	Paul	Champlin	4610	4325	2025-06-24 19:48:54.581559-05	nndz-WkNPd3hMdjhoQT09	4511	t	31.10	0	5	0.00		2025-06-24 19:48:54.581559-05	0	0	0	0.00	\N
328252	\N	Ted	Cunneen	4610	4325	2025-06-24 19:48:54.581559-05	nndz-WkNPd3hMajlnZz09	4511	t	28.70	4	7	36.40		2025-06-24 19:48:54.581559-05	0	0	0	0.00	\N
328253	\N	Kian	Dowlatshahi	4610	4325	2025-06-24 19:48:54.581559-05	nndz-WkNHNXdMcjVqUT09	4511	t	16.80	16	6	72.70		2025-06-24 19:48:54.581559-05	0	0	0	0.00	\N
328254	\N	Paul	Furlow	4610	4325	2025-06-24 19:48:54.581559-05	nndz-WkNPd3g3ejlnQT09	4511	t	33.00	3	6	33.30		2025-06-24 19:48:54.581559-05	0	0	0	0.00	\N
328255	\N	Jamie	Green	4610	4325	2025-06-24 19:48:54.581559-05	nndz-WkNPd3hMM3dnZz09	4511	t	21.70	17	9	65.40		2025-06-24 19:48:54.581559-05	0	0	0	0.00	\N
328256	\N	Peter	Hammond	4610	4325	2025-06-24 19:48:54.581559-05	nndz-WkNPd3hMajVodz09	4511	t	11.40	10	8	55.60		2025-06-24 19:48:54.581559-05	0	0	0	0.00	\N
328257	\N	Will	Kernahan	4610	4325	2025-06-24 19:48:54.581559-05	nndz-WkNPd3g3ejVnQT09	4511	t	35.30	1	9	10.00		2025-06-24 19:48:54.581559-05	0	0	0	0.00	\N
328258	\N	Jon	Lothan	4610	4325	2025-06-24 19:48:54.581559-05	nndz-WkNDNnhyYjVodz09	4511	t	14.20	15	2	88.20		2025-06-24 19:48:54.581559-05	0	0	0	0.00	\N
328259	\N	Mike	Morrison	4610	4325	2025-06-24 19:48:54.581559-05	nndz-WkNPd3hMdjdodz09	4511	t	20.40	5	5	50.00		2025-06-24 19:48:54.581559-05	0	0	0	0.00	\N
328260	\N	Scott	Olson	4610	4325	2025-06-24 19:48:54.581559-05	nndz-WkNPd3hMdjhoZz09	4511	t	25.60	9	5	64.30		2025-06-24 19:48:54.581559-05	0	0	0	0.00	\N
328261	\N	Jordan	Shtulman	4610	4325	2025-06-24 19:48:54.581559-05	nndz-WkNPd3hyZjdoZz09	4511	t	20.40	6	6	50.00		2025-06-24 19:48:54.581559-05	0	0	0	0.00	\N
328262	\N	Dylan	Steffens	4610	4325	2025-06-24 19:48:54.581559-05	nndz-WkM2K3hyejloUT09	4511	t	16.30	10	2	83.30		2025-06-24 19:48:54.581559-05	0	0	0	0.00	\N
328263	\N	Josh	Hinterlong	4626	4306	2025-06-24 19:48:54.581559-05	nndz-WkNPd3hMZjVoUT09	4511	t	11.80	15	6	71.40	C	2025-06-24 19:48:54.581559-05	0	0	0	0.00	13824
328264	\N	Brad	Hunter	4626	4306	2025-06-24 19:48:54.581559-05	nndz-WkNPd3hMZjVqQT09	4511	t	20.30	8	2	80.00	CC	2025-06-24 19:48:54.581559-05	0	0	0	0.00	13824
328265	\N	Charlie	Boyd	4626	4306	2025-06-24 19:48:54.581559-05	nndz-WkNPd3g3MzRodz09	4511	t	21.30	12	7	63.20		2025-06-24 19:48:54.581559-05	0	0	0	0.00	13824
328266	\N	Chris	Broughton	4626	4306	2025-06-24 19:48:54.581559-05	nndz-WkNPd3liLzZnUT09	4511	t	23.40	9	9	50.00		2025-06-24 19:48:54.581559-05	0	0	0	0.00	13824
328267	\N	Tim	Dull	4626	4306	2025-06-24 19:48:54.581559-05	nndz-WkNDNnlMbjhnUT09	4511	t	22.90	9	5	64.30		2025-06-24 19:48:54.581559-05	0	0	0	0.00	13824
328268	\N	Greg	Embree	4626	4306	2025-06-24 19:48:54.581559-05	nndz-WkNHeHdML3hnUT09	4511	t	23.90	13	6	68.40		2025-06-24 19:48:54.581559-05	0	0	0	0.00	13824
328269	\N	Jeff	Keckley	4626	4306	2025-06-24 19:48:54.581559-05	nndz-WkNPd3hMZjZqQT09	4511	t	24.40	8	6	57.10		2025-06-24 19:48:54.581559-05	0	0	0	0.00	13824
328270	\N	Timbo	Martin	4626	4306	2025-06-24 19:48:54.581559-05	nndz-WkNPd3hMZjhoQT09	4511	t	21.90	12	5	70.60		2025-06-24 19:48:54.581559-05	0	0	0	0.00	13824
328271	\N	Rob	Neuman	4626	4306	2025-06-24 19:48:54.581559-05	nndz-WkNPd3hMZjVoQT09	4511	t	17.80	11	4	73.30		2025-06-24 19:48:54.581559-05	0	0	0	0.00	13824
328272	\N	Kyle	Rudman	4626	4306	2025-06-24 19:48:54.581559-05	nndz-WkM2NXhyNzVoQT09	4511	t	\N	0	0	0.00		2025-06-24 19:48:54.581559-05	0	0	0	0.00	13824
328273	\N	Matt	Schuler	4626	4306	2025-06-24 19:48:54.581559-05	nndz-WkNPd3g3MzdnUT09	4511	t	19.30	24	12	66.70		2025-06-24 19:48:54.581559-05	0	0	0	0.00	13824
328274	\N	Kevin	Lannert	4632	4306	2025-06-24 19:48:54.581559-05	nndz-WkNPd3hMbitoUT09	4511	t	29.30	6	10	37.50	C	2025-06-24 19:48:54.581559-05	0	0	0	0.00	13854
328275	\N	Jim	Bowers	4632	4306	2025-06-24 19:48:54.581559-05	nndz-WkNPd3hMMzhndz09	4511	t	18.90	10	4	71.40		2025-06-24 19:48:54.581559-05	0	0	0	0.00	13854
328276	\N	Jeff	Ellithorpe	4632	4306	2025-06-24 19:48:54.581559-05	nndz-WkNDK3lMZjhqQT09	4511	t	26.00	4	5	44.40		2025-06-24 19:48:54.581559-05	0	0	0	0.00	13854
328277	\N	Todd	Fisher	4632	4306	2025-06-24 19:48:54.581559-05	nndz-WkNPd3hMcjVoUT09	4511	t	27.10	0	1	0.00		2025-06-24 19:48:54.581559-05	0	0	0	0.00	13854
328278	\N	Rob	Hopkins	4632	4306	2025-06-24 19:48:54.581559-05	nndz-WkNPd3hMeitoQT09	4511	t	27.80	4	12	25.00		2025-06-24 19:48:54.581559-05	0	0	0	0.00	13854
328279	\N	Ryan	Keefe	4632	4306	2025-06-24 19:48:54.581559-05	nndz-WkNHeHc3Zi9oQT09	4511	t	10.00	20	7	74.10		2025-06-24 19:48:54.581559-05	0	0	0	0.00	13854
328280	\N	Patrick	McGuigan	4632	4306	2025-06-24 19:48:54.581559-05	nndz-WkNHeHdiZjRnZz09	4511	t	24.60	6	6	50.00		2025-06-24 19:48:54.581559-05	0	0	0	0.00	13854
328281	\N	Bob	Schulz	4632	4306	2025-06-24 19:48:54.581559-05	nndz-WkM2L3dMZnhnUT09	4511	t	37.70	1	3	25.00		2025-06-24 19:48:54.581559-05	0	0	0	0.00	13854
328282	\N	Charlie	Usher	4632	4306	2025-06-24 19:48:54.581559-05	nndz-WkNPd3hMei9odz09	4511	t	23.20	4	7	36.40		2025-06-24 19:48:54.581559-05	0	0	0	0.00	13854
328283	\N	Mikey	Usher	4632	4306	2025-06-24 19:48:54.581559-05	nndz-WkNHeHdiZjVqUT09	4511	t	28.60	5	10	33.30		2025-06-24 19:48:54.581559-05	0	0	0	0.00	13854
328284	\N	Marc	Veverka	4632	4306	2025-06-24 19:48:54.581559-05	nndz-WkNPd3hMei9nZz09	4511	t	18.20	6	6	50.00		2025-06-24 19:48:54.581559-05	0	0	0	0.00	13854
328285	\N	Pat	Walker	4632	4306	2025-06-24 19:48:54.581559-05	nndz-WkNPd3hMaitodz09	4511	t	23.40	5	5	50.00		2025-06-24 19:48:54.581559-05	0	0	0	0.00	13854
328286	\N	Robert	Weber	4632	4306	2025-06-24 19:48:54.581559-05	nndz-WkNPd3hMcjVnQT09	4511	t	20.50	12	9	57.10		2025-06-24 19:48:54.581559-05	0	0	0	0.00	13854
328287	\N	Rob	Young	4632	4306	2025-06-24 19:48:54.581559-05	nndz-WkNPd3g3MzRqQT09	4511	t	18.20	18	10	64.30		2025-06-24 19:48:54.581559-05	0	0	0	0.00	13854
328288	\N	Matt	Ohlsen	4636	4306	2025-06-24 19:48:54.581559-05	nndz-WkNPd3hMdjZoZz09	4511	t	16.00	14	4	77.80	C	2025-06-24 19:48:54.581559-05	0	0	0	0.00	13898
328289	\N	Josh	Wittenberg	4636	4306	2025-06-24 19:48:54.581559-05	nndz-WkNPd3hMZitnQT09	4511	t	14.60	9	11	45.00	CC	2025-06-24 19:48:54.581559-05	0	0	0	0.00	13898
328290	\N	Stephan	Brown	4636	4306	2025-06-24 19:48:54.581559-05	nndz-WkNPd3hMYndoZz09	4511	t	22.90	15	4	78.90		2025-06-24 19:48:54.581559-05	0	0	0	0.00	13898
328291	\N	Matt	Davis	4636	4306	2025-06-24 19:48:54.581559-05	nndz-WkNPd3hMMzlnUT09	4511	t	33.00	0	0	0.00		2025-06-24 19:48:54.581559-05	0	0	0	0.00	13898
328292	\N	Brandon	Dechter	4636	4306	2025-06-24 19:48:54.581559-05	nndz-WkNHNXdiZjhqQT09	4511	t	19.60	15	4	78.90		2025-06-24 19:48:54.581559-05	0	0	0	0.00	13898
328293	\N	Jim	Miller	4636	4306	2025-06-24 19:48:54.581559-05	nndz-WkNPd3liYjRoZz09	4511	t	21.30	21	11	65.60		2025-06-24 19:48:54.581559-05	0	0	0	0.00	13898
328294	\N	Roger	Mills	4636	4306	2025-06-24 19:48:54.581559-05	nndz-WkNHeHhidndoZz09	4511	t	23.90	12	3	80.00		2025-06-24 19:48:54.581559-05	0	0	0	0.00	13898
328295	\N	Doug	Oomen	4636	4306	2025-06-24 19:48:54.581559-05	nndz-WkNHeHdyeitnQT09	4511	t	22.90	22	9	71.00		2025-06-24 19:48:54.581559-05	0	0	0	0.00	13898
328296	\N	Sanjiv	Pillai	4636	4306	2025-06-24 19:48:54.581559-05	nndz-WkNDOXhiai9odz09	4511	t	16.00	12	3	80.00		2025-06-24 19:48:54.581559-05	0	0	0	0.00	13898
328297	\N	Mike	Stoja	4636	4306	2025-06-24 19:48:54.581559-05	nndz-WkNPd3hMYndnZz09	4511	t	16.80	8	11	42.10		2025-06-24 19:48:54.581559-05	0	0	0	0.00	13898
328298	\N	David	Weibel	4636	4306	2025-06-24 19:48:54.581559-05	nndz-WkNPd3hMYndodz09	4511	t	26.30	6	1	85.70		2025-06-24 19:48:54.581559-05	0	0	0	0.00	13898
328299	\N	Sean	Owen	4640	4306	2025-06-24 19:48:54.581559-05	nndz-WkNPd3hMcitndz09	4511	t	22.90	4	3	57.10	C	2025-06-24 19:48:54.581559-05	0	0	0	0.00	14003
328300	\N	Rishi	Goel	4640	4306	2025-06-24 19:48:54.581559-05	nndz-WkNPd3hMZjZoQT09	4511	t	15.10	18	8	69.20	CC	2025-06-24 19:48:54.581559-05	0	0	0	0.00	14003
328301	\N	Jack	Callahan	4640	4306	2025-06-24 19:48:54.581559-05	nndz-WkNPd3hyYitnQT09	4511	t	25.10	20	14	58.80		2025-06-24 19:48:54.581559-05	0	0	0	0.00	14003
328302	\N	Jason	Ciaglo	4640	4306	2025-06-24 19:48:54.581559-05	nndz-WkNPd3hMcitqQT09	4511	t	26.20	8	10	44.40		2025-06-24 19:48:54.581559-05	0	0	0	0.00	14003
328303	\N	Jack	Farr	4640	4306	2025-06-24 19:48:54.581559-05	nndz-WkNHeHhicjdoQT09	4511	t	24.90	10	5	66.70		2025-06-24 19:48:54.581559-05	0	0	0	0.00	14003
328304	\N	Paul	Fortman	4640	4306	2025-06-24 19:48:54.581559-05	nndz-WkNPd3g3L3hoUT09	4511	t	26.00	8	12	40.00		2025-06-24 19:48:54.581559-05	0	0	0	0.00	14003
328305	\N	Andrew	Heinlein	4640	4306	2025-06-24 19:48:54.581559-05	nndz-WkNPd3hMZjRnZz09	4511	t	21.10	17	8	68.00		2025-06-24 19:48:54.581559-05	0	0	0	0.00	14003
328306	\N	John	M Weinlader	4640	4306	2025-06-24 19:48:54.581559-05	nndz-WkNPd3g3djlnUT09	4511	t	26.40	11	14	44.00		2025-06-24 19:48:54.581559-05	0	0	0	0.00	14003
328307	\N	Marc	McCallister	4640	4306	2025-06-24 19:48:54.581559-05	nndz-WkNPd3hMcjlqUT09	4511	t	19.40	2	0	100.00		2025-06-24 19:48:54.581559-05	0	0	0	0.00	14003
328308	\N	David	Parker	4640	4306	2025-06-24 19:48:54.581559-05	nndz-WkNPd3hMMytqQT09	4511	t	22.20	6	3	66.70		2025-06-24 19:48:54.581559-05	0	0	0	0.00	14003
328309	\N	Tim	Murphy	4644	4306	2025-06-24 19:48:54.581559-05	nndz-WkNPd3hMYjRnQT09	4511	t	35.00	2	6	25.00	C	2025-06-24 19:48:54.581559-05	0	0	0	0.00	14054
328310	\N	Will	Black	4644	4306	2025-06-24 19:48:54.581559-05	nndz-WkNPd3hMbjdnUT09	4511	t	32.90	4	11	26.70		2025-06-24 19:48:54.581559-05	0	0	0	0.00	14054
328311	\N	Mike	Cagney	4644	4306	2025-06-24 19:48:54.581559-05	nndz-WkNPd3hMbjloQT09	4511	t	28.40	2	13	13.30		2025-06-24 19:48:54.581559-05	0	0	0	0.00	14054
328312	\N	Bob	Dold	4644	4306	2025-06-24 19:48:54.581559-05	nndz-WkNPd3hMbjhodz09	4511	t	23.20	3	8	27.30		2025-06-24 19:48:54.581559-05	0	0	0	0.00	14054
328313	\N	Jerry	Ehlinger	4644	4306	2025-06-24 19:48:54.581559-05	nndz-WkNPd3hMZjdnZz09	4511	t	25.10	8	21	27.60		2025-06-24 19:48:54.581559-05	0	0	0	0.00	14054
328314	\N	Mike	Judy	4644	4306	2025-06-24 19:48:54.581559-05	nndz-WkNPd3hMbjhoQT09	4511	t	27.80	1	6	14.30		2025-06-24 19:48:54.581559-05	0	0	0	0.00	14054
328315	\N	Patrick	Leydon	4644	4306	2025-06-24 19:48:54.581559-05	nndz-WkNPd3hMdi9oUT09	4511	t	27.50	5	8	38.50		2025-06-24 19:48:54.581559-05	0	0	0	0.00	14054
328316	\N	Matt	Miller	4644	4306	2025-06-24 19:48:54.581559-05	nndz-WkNPd3hMYjRnUT09	4511	t	27.80	7	15	31.80		2025-06-24 19:48:54.581559-05	0	0	0	0.00	14054
328317	\N	Daniel	Potter	4644	4306	2025-06-24 19:48:54.581559-05	nndz-WkNPd3hMcjdnZz09	4511	t	25.20	4	10	28.60		2025-06-24 19:48:54.581559-05	0	0	0	0.00	14054
328318	\N	Andres	Soruco	4644	4306	2025-06-24 19:48:54.581559-05	nndz-WkNPd3hMbjlnUT09	4511	t	21.00	0	0	0.00		2025-06-24 19:48:54.581559-05	0	0	0	0.00	14054
328319	\N	Daniel	Mortell	4645	4306	2025-06-24 19:48:54.581559-05	nndz-WkNPd3hyajZndz09	4511	t	28.40	5	9	35.70	C	2025-06-24 19:48:54.581559-05	0	0	0	0.00	14066
328320	\N	Erik	Billings	4645	4306	2025-06-24 19:48:54.581559-05	nndz-WkM2L3c3bndodz09	4511	t	23.00	21	13	61.80		2025-06-24 19:48:54.581559-05	0	0	0	0.00	14066
328321	\N	Pat	Clark	4645	4306	2025-06-24 19:48:54.581559-05	nndz-WkNPd3g3bndndz09	4511	t	22.00	17	10	63.00		2025-06-24 19:48:54.581559-05	0	0	0	0.00	14066
328322	\N	John	Feiten	4645	4306	2025-06-24 19:48:54.581559-05	nndz-WkM2L3hyYi9ndz09	4511	t	31.50	4	8	33.30		2025-06-24 19:48:54.581559-05	0	0	0	0.00	14066
328323	\N	AJ	Llaneza	4645	4306	2025-06-24 19:48:54.581559-05	nndz-WkNDNnhyZjVqQT09	4511	t	19.50	11	8	57.90		2025-06-24 19:48:54.581559-05	0	0	0	0.00	14066
328324	\N	Richard	Mortell	4645	4306	2025-06-24 19:48:54.581559-05	nndz-WkNPd3hMdjRodz09	4511	t	28.90	7	9	43.80		2025-06-24 19:48:54.581559-05	0	0	0	0.00	14066
328325	\N	Keegan	O'Brien	4645	4306	2025-06-24 19:48:54.581559-05	nndz-WkNHeHhMZjRodz09	4511	t	17.80	18	10	64.30		2025-06-24 19:48:54.581559-05	0	0	0	0.00	14066
\.


--
-- TOC entry 4150 (class 0 OID 46535)
-- Dependencies: 236
-- Data for Name: poll_choices; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.poll_choices (id, poll_id, choice_text) FROM stdin;
43	21	Drill
44	21	Practice
45	22	Trump
46	22	Kamala
47	23	Red
48	23	Blue
53	26	Drill
54	26	Practice
55	27	Practice
56	27	Drill
57	28	C1
58	28	C2
61	30	Drill
62	30	Practice
63	31	1
64	31	2
70	34	Drill
71	34	Practice
\.


--
-- TOC entry 4152 (class 0 OID 46541)
-- Dependencies: 238
-- Data for Name: poll_responses; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.poll_responses (id, poll_id, choice_id, player_id, responded_at) FROM stdin;
10	21	43	96023	2025-06-18 16:27:25.008057-05
11	22	46	96023	2025-06-18 16:35:43.341243-05
12	23	47	96023	2025-06-18 17:48:05.922462-05
13	23	47	101094	2025-06-18 19:06:52.571662-05
14	26	53	103664	2025-06-19 10:25:53.768911-05
15	27	55	118952	2025-06-19 15:28:30.567511-05
16	30	61	168833	2025-06-21 06:32:27.722887-05
17	31	63	312245	2025-06-22 07:29:49.497282-05
18	34	70	313005	2025-06-23 21:21:48.300159-05
\.


--
-- TOC entry 4154 (class 0 OID 46546)
-- Dependencies: 240
-- Data for Name: polls; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.polls (id, team_id, created_by, question, created_at) FROM stdin;
21	\N	43	Drill or practice	2025-06-18 15:56:22.773523-05
22	\N	49	Who did you vote for	2025-06-18 16:02:31.110347-05
23	\N	49	What is your favorite color	2025-06-18 16:50:39.90037-05
26	\N	43	Drill or practice?	2025-06-19 10:25:48.407025-05
27	678	43	Practice or Drill?	2025-06-19 15:28:21.525037-05
28	1921	72	Test poll for series 38	2025-06-20 13:44:09.904179-05
30	3201	43	Drill or practice	2025-06-21 06:32:18.168805-05
31	12341	79	test	2025-06-22 07:29:45.173606-05
34	12325	43	Should we do a drill with Olga or a practice next week?	2025-06-23 21:21:42.460526-05
\.


--
-- TOC entry 4156 (class 0 OID 46553)
-- Dependencies: 242
-- Data for Name: pro_lessons; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.pro_lessons (id, user_email, pro_id, lesson_date, lesson_time, focus_areas, notes, status, created_at, updated_at) FROM stdin;
\.


--
-- TOC entry 4158 (class 0 OID 46562)
-- Dependencies: 244
-- Data for Name: pros; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.pros (id, name, bio, specialties, hourly_rate, image_url, phone, email, is_active, created_at, updated_at) FROM stdin;
5	Olga Martinsone	Director of Racquets, Tennaqua Swim & Racquet Club, Deerfield, IL. I am a USPTA certified Tennis/Paddle Elite Professional. I began playing tennis when I was ten years old in my home country of Latvia where I played for the Latvian National Tennis Team. Additionally, I played in several International Tennis Federation (ITF) tournaments throughout Europe and the Middle East.	Overheads, Volleys, Court Positioning	80.00	/static/images/olga_martinsone.jpg	555-0101	olga.martinsone@tennaqua.com	t	2025-06-24 07:09:15.193832	2025-06-24 09:39:33.906936
6	Billy Friedman, Tennis Pro	The NJCAA Region 4 Player-of-the-Year award tops off a season where Billy was also the Illinois Skyway Collegiate Conference Player-of-the-Year. Billy was the Region 4 champion at number two singles and number one doubles the past two years. Billy's undefeated record at number one singles led the CLC Men's Tennis Team to the NJCAA Men's Tennis National Tournament, a second place finish in both the region and conference, and a 8-2 team record.	Serves, Backhands, Mental Game	75.00	/static/images/billy_friedman.jpg	555-0102	billy.friedman@rallytennis.com	t	2025-06-24 07:09:15.196649	2025-06-24 09:39:33.91598
7	Mike Simms, Tennis Pro	Experienced tennis professional with over 10 years of coaching experience. Specializes in developing players of all skill levels, from beginners learning the fundamentals to advanced players refining their technique. Known for his patient teaching style and ability to break down complex techniques into manageable steps.	Forehands, Footwork, Strategy	70.00	/static/images/mike_simms.jpg	555-0103	mike.simms@rallytennis.com	t	2025-06-24 07:09:15.200492	2025-06-24 09:39:33.923741
\.


--
-- TOC entry 4160 (class 0 OID 46571)
-- Dependencies: 246
-- Data for Name: schedule; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.schedule (id, match_date, match_time, home_team, away_team, location, created_at, league_id, home_team_id, away_team_id) FROM stdin;
\.


--
-- TOC entry 4162 (class 0 OID 46578)
-- Dependencies: 248
-- Data for Name: series; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.series (id, name, updated_at) FROM stdin;
4257	Bannockburn	2025-06-24 19:48:53.467096-05
4258	Boys	2025-06-24 19:48:53.467096-05
4259	Chicago	2025-06-24 19:48:53.467096-05
4260	Chicago 1	2025-06-24 19:48:53.467096-05
4261	Chicago 10	2025-06-24 19:48:53.467096-05
4262	Chicago 11	2025-06-24 19:48:53.467096-05
4263	Chicago 11 SW	2025-06-24 19:48:53.467096-05
4264	Chicago 12	2025-06-24 19:48:53.467096-05
4265	Chicago 13	2025-06-24 19:48:53.467096-05
4266	Chicago 13 SW	2025-06-24 19:48:53.467096-05
4267	Chicago 14	2025-06-24 19:48:53.467096-05
4268	Chicago 15	2025-06-24 19:48:53.467096-05
4269	Chicago 15 SW	2025-06-24 19:48:53.467096-05
4270	Chicago 16	2025-06-24 19:48:53.467096-05
4271	Chicago 17	2025-06-24 19:48:53.467096-05
4272	Chicago 17 SW	2025-06-24 19:48:53.467096-05
4273	Chicago 18	2025-06-24 19:48:53.467096-05
4274	Chicago 19	2025-06-24 19:48:53.467096-05
4275	Chicago 19 SW	2025-06-24 19:48:53.467096-05
4276	Chicago 2	2025-06-24 19:48:53.467096-05
4277	Chicago 20	2025-06-24 19:48:53.467096-05
4278	Chicago 21	2025-06-24 19:48:53.467096-05
4279	Chicago 21 SW	2025-06-24 19:48:53.467096-05
4280	Chicago 22	2025-06-24 19:48:53.467096-05
4281	Chicago 23	2025-06-24 19:48:53.467096-05
4282	Chicago 23 SW	2025-06-24 19:48:53.467096-05
4283	Chicago 24	2025-06-24 19:48:53.467096-05
4284	Chicago 25	2025-06-24 19:48:53.467096-05
4285	Chicago 25 SW	2025-06-24 19:48:53.467096-05
4286	Chicago 26	2025-06-24 19:48:53.467096-05
4287	Chicago 27	2025-06-24 19:48:53.467096-05
4288	Chicago 27 SW	2025-06-24 19:48:53.467096-05
4289	Chicago 28	2025-06-24 19:48:53.467096-05
4290	Chicago 29	2025-06-24 19:48:53.467096-05
4291	Chicago 29 SW	2025-06-24 19:48:53.467096-05
4292	Chicago 3	2025-06-24 19:48:53.467096-05
4293	Chicago 3.0 & Under Thur	2025-06-24 19:48:53.467096-05
4294	Chicago 3.5 & Under Sat	2025-06-24 19:48:53.467096-05
4295	Chicago 3.5 & Under Wed	2025-06-24 19:48:53.467096-05
4296	Chicago 30	2025-06-24 19:48:53.467096-05
4297	Chicago 31	2025-06-24 19:48:53.467096-05
4298	Chicago 32	2025-06-24 19:48:53.467096-05
4299	Chicago 33	2025-06-24 19:48:53.467096-05
4300	Chicago 34	2025-06-24 19:48:53.467096-05
4301	Chicago 35	2025-06-24 19:48:53.467096-05
4302	Chicago 36	2025-06-24 19:48:53.467096-05
4303	Chicago 37	2025-06-24 19:48:53.467096-05
4304	Chicago 38	2025-06-24 19:48:53.467096-05
4305	Chicago 39	2025-06-24 19:48:53.467096-05
4306	Chicago 4	2025-06-24 19:48:53.467096-05
4307	Chicago 4.0 & Under Fri	2025-06-24 19:48:53.467096-05
4308	Chicago 4.0 & Under Sat	2025-06-24 19:48:53.467096-05
4309	Chicago 4.0 & Under Wed	2025-06-24 19:48:53.467096-05
4310	Chicago 4.0 Singles Sun	2025-06-24 19:48:53.467096-05
4311	Chicago 4.5 & Under Fri	2025-06-24 19:48:53.467096-05
4312	Chicago 4.5 & Under Sat	2025-06-24 19:48:53.467096-05
4313	Chicago 4.5 Singles Sun	2025-06-24 19:48:53.467096-05
4314	Chicago 4.5+ Sat	2025-06-24 19:48:53.467096-05
4315	Chicago 5	2025-06-24 19:48:53.467096-05
4316	Chicago 6	2025-06-24 19:48:53.467096-05
4317	Chicago 7	2025-06-24 19:48:53.467096-05
4318	Chicago 7 SW	2025-06-24 19:48:53.467096-05
4319	Chicago 8	2025-06-24 19:48:53.467096-05
4320	Chicago 9	2025-06-24 19:48:53.467096-05
4321	Chicago 9 SW	2025-06-24 19:48:53.467096-05
4322	Chicago 99	2025-06-24 19:48:53.467096-05
4323	Chicago Bannockburn 1	2025-06-24 19:48:53.467096-05
4324	Chicago Bannockburn 2	2025-06-24 19:48:53.467096-05
4325	Chicago Chicago	2025-06-24 19:48:53.467096-05
4326	Chicago Chicago 1	2025-06-24 19:48:53.467096-05
4327	Chicago Chicago 2	2025-06-24 19:48:53.467096-05
4328	Chicago East 1	2025-06-24 19:48:53.467096-05
4329	Chicago East 2	2025-06-24 19:48:53.467096-05
4330	Division 1	2025-06-24 19:48:53.467096-05
4331	Division 10	2025-06-24 19:48:53.467096-05
4332	Division 11	2025-06-24 19:48:53.467096-05
4333	Division 12	2025-06-24 19:48:53.467096-05
4334	Division 13	2025-06-24 19:48:53.467096-05
4335	Division 14	2025-06-24 19:48:53.467096-05
4336	Division 14a	2025-06-24 19:48:53.467096-05
4337	Division 14b	2025-06-24 19:48:53.467096-05
4338	Division 15	2025-06-24 19:48:53.467096-05
4339	Division 16	2025-06-24 19:48:53.467096-05
4340	Division 16a	2025-06-24 19:48:53.467096-05
4341	Division 16b	2025-06-24 19:48:53.467096-05
4342	Division 17	2025-06-24 19:48:53.467096-05
4343	Division 19	2025-06-24 19:48:53.467096-05
4344	Division 1a	2025-06-24 19:48:53.467096-05
4345	Division 1b	2025-06-24 19:48:53.467096-05
4346	Division 2	2025-06-24 19:48:53.467096-05
4347	Division 2a	2025-06-24 19:48:53.467096-05
4348	Division 2b	2025-06-24 19:48:53.467096-05
4349	Division 3	2025-06-24 19:48:53.467096-05
4350	Division 3.0	2025-06-24 19:48:53.467096-05
4351	Division 3a	2025-06-24 19:48:53.467096-05
4352	Division 3b	2025-06-24 19:48:53.467096-05
4353	Division 4	2025-06-24 19:48:53.467096-05
4354	Division 4.0	2025-06-24 19:48:53.467096-05
4355	Division 5	2025-06-24 19:48:53.467096-05
4356	Division 5a	2025-06-24 19:48:53.467096-05
4357	Division 5b	2025-06-24 19:48:53.467096-05
4358	Division 6	2025-06-24 19:48:53.467096-05
4359	Division 7	2025-06-24 19:48:53.467096-05
4360	Division 8	2025-06-24 19:48:53.467096-05
4361	Division 8a	2025-06-24 19:48:53.467096-05
4362	Division 8b	2025-06-24 19:48:53.467096-05
4363	Division 9	2025-06-24 19:48:53.467096-05
4364	East	2025-06-24 19:48:53.467096-05
4365	Girls	2025-06-24 19:48:53.467096-05
4366	Libertyville	2025-06-24 19:48:53.467096-05
4367	Lincolnshire	2025-06-24 19:48:53.467096-05
4368	Open Fri	2025-06-24 19:48:53.467096-05
4369	Palatine	2025-06-24 19:48:53.467096-05
4370	S1	2025-06-24 19:48:53.467096-05
4371	S10	2025-06-24 19:48:53.467096-05
4372	S11	2025-06-24 19:48:53.467096-05
4373	S11 SW	2025-06-24 19:48:53.467096-05
4374	S12	2025-06-24 19:48:53.467096-05
4375	S13	2025-06-24 19:48:53.467096-05
4376	S13 SW	2025-06-24 19:48:53.467096-05
4377	S14	2025-06-24 19:48:53.467096-05
4378	S15	2025-06-24 19:48:53.467096-05
4379	S15 SW	2025-06-24 19:48:53.467096-05
4380	S16	2025-06-24 19:48:53.467096-05
4381	S17	2025-06-24 19:48:53.467096-05
4382	S17 SW	2025-06-24 19:48:53.467096-05
4383	S19 SW	2025-06-24 19:48:53.467096-05
4384	S2	2025-06-24 19:48:53.467096-05
4385	S21 SW	2025-06-24 19:48:53.467096-05
4386	S23 SW	2025-06-24 19:48:53.467096-05
4387	S25 SW	2025-06-24 19:48:53.467096-05
4388	S27 SW	2025-06-24 19:48:53.467096-05
4389	S29 SW	2025-06-24 19:48:53.467096-05
4390	S2A	2025-06-24 19:48:53.467096-05
4391	S2B	2025-06-24 19:48:53.467096-05
4392	S3	2025-06-24 19:48:53.467096-05
4393	S3.0 & Under Thur	2025-06-24 19:48:53.467096-05
4394	S3.0 - 3.5 Singles Thur	2025-06-24 19:48:53.467096-05
4395	S3.5 & Under Sat	2025-06-24 19:48:53.467096-05
4396	S3.5 & Under Wed	2025-06-24 19:48:53.467096-05
4397	S4	2025-06-24 19:48:53.467096-05
4398	S4.0 & Under Fri	2025-06-24 19:48:53.467096-05
4399	S4.0 & Under Sat	2025-06-24 19:48:53.467096-05
4400	S4.0 & Under Wed	2025-06-24 19:48:53.467096-05
4401	S4.0 - 4.5 Singles Thur	2025-06-24 19:48:53.467096-05
4402	S4.0 Singles Sun	2025-06-24 19:48:53.467096-05
4403	S4.5 & Under Fri	2025-06-24 19:48:53.467096-05
4404	S4.5 & Under Sat	2025-06-24 19:48:53.467096-05
4405	S4.5 Singles Sun	2025-06-24 19:48:53.467096-05
4406	S4.5+ Sat	2025-06-24 19:48:53.467096-05
4407	S5	2025-06-24 19:48:53.467096-05
4408	S6	2025-06-24 19:48:53.467096-05
4409	S7	2025-06-24 19:48:53.467096-05
4410	S7 SW	2025-06-24 19:48:53.467096-05
4411	S8	2025-06-24 19:48:53.467096-05
4412	S9	2025-06-24 19:48:53.467096-05
4413	S9 SW	2025-06-24 19:48:53.467096-05
4414	SA	2025-06-24 19:48:53.467096-05
4415	SB	2025-06-24 19:48:53.467096-05
4416	SBoys	2025-06-24 19:48:53.467096-05
4417	SC	2025-06-24 19:48:53.467096-05
4418	SD	2025-06-24 19:48:53.467096-05
4419	SE	2025-06-24 19:48:53.467096-05
4420	SF	2025-06-24 19:48:53.467096-05
4421	SG	2025-06-24 19:48:53.467096-05
4422	SGirls	2025-06-24 19:48:53.467096-05
4423	SH	2025-06-24 19:48:53.467096-05
4424	SI	2025-06-24 19:48:53.467096-05
4425	SJ	2025-06-24 19:48:53.467096-05
4426	SK	2025-06-24 19:48:53.467096-05
4427	SLegends	2025-06-24 19:48:53.467096-05
4428	SOpen Fri	2025-06-24 19:48:53.467096-05
4429	SSN	2025-06-24 19:48:53.467096-05
4430	Series 1	2025-06-24 19:48:53.467096-05
4431	Series 2A	2025-06-24 19:48:53.467096-05
4432	Series 2B	2025-06-24 19:48:53.467096-05
4433	Series 3	2025-06-24 19:48:53.467096-05
4434	Series A	2025-06-24 19:48:53.467096-05
4435	Series eries 1	2025-06-24 19:48:53.467096-05
4436	Series eries 10	2025-06-24 19:48:53.467096-05
4437	Series eries 11	2025-06-24 19:48:53.467096-05
4438	Series eries 12	2025-06-24 19:48:53.467096-05
4439	Series eries 13	2025-06-24 19:48:53.467096-05
4440	Series eries 14	2025-06-24 19:48:53.467096-05
4441	Series eries 15	2025-06-24 19:48:53.467096-05
4442	Series eries 16	2025-06-24 19:48:53.467096-05
4443	Series eries 17	2025-06-24 19:48:53.467096-05
4444	Series eries 2	2025-06-24 19:48:53.467096-05
4445	Series eries 2A	2025-06-24 19:48:53.467096-05
4446	Series eries 2B	2025-06-24 19:48:53.467096-05
4447	Series eries 3	2025-06-24 19:48:53.467096-05
4448	Series eries 4	2025-06-24 19:48:53.467096-05
4449	Series eries 5	2025-06-24 19:48:53.467096-05
4450	Series eries 6	2025-06-24 19:48:53.467096-05
4451	Series eries 7	2025-06-24 19:48:53.467096-05
4452	Series eries 8	2025-06-24 19:48:53.467096-05
4453	Series eries 9	2025-06-24 19:48:53.467096-05
4454	Series eries A	2025-06-24 19:48:53.467096-05
4455	Series eries B	2025-06-24 19:48:53.467096-05
4456	Series eries C	2025-06-24 19:48:53.467096-05
4457	Series eries D	2025-06-24 19:48:53.467096-05
4458	Series eries E	2025-06-24 19:48:53.467096-05
4459	Series eries F	2025-06-24 19:48:53.467096-05
4460	Series eries G	2025-06-24 19:48:53.467096-05
4461	Series eries H	2025-06-24 19:48:53.467096-05
4462	Series eries I	2025-06-24 19:48:53.467096-05
4463	Series eries J	2025-06-24 19:48:53.467096-05
4464	Series eries K	2025-06-24 19:48:53.467096-05
4465	Series eries SN	2025-06-24 19:48:53.467096-05
4466	West	2025-06-24 19:48:53.467096-05
\.


--
-- TOC entry 4164 (class 0 OID 46583)
-- Dependencies: 250
-- Data for Name: series_leagues; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.series_leagues (id, series_id, league_id, created_at) FROM stdin;
3641	4330	4513	2025-06-24 19:48:53.49247-05
3642	4344	4513	2025-06-24 19:48:53.49247-05
3643	4345	4513	2025-06-24 19:48:53.49247-05
3644	4346	4513	2025-06-24 19:48:53.49247-05
3645	4347	4513	2025-06-24 19:48:53.49247-05
3646	4348	4513	2025-06-24 19:48:53.49247-05
3647	4349	4513	2025-06-24 19:48:53.49247-05
3648	4351	4513	2025-06-24 19:48:53.49247-05
3649	4352	4513	2025-06-24 19:48:53.49247-05
3650	4353	4513	2025-06-24 19:48:53.49247-05
3651	4355	4513	2025-06-24 19:48:53.49247-05
3652	4356	4513	2025-06-24 19:48:53.49247-05
3653	4357	4513	2025-06-24 19:48:53.49247-05
3654	4358	4513	2025-06-24 19:48:53.49247-05
3655	4359	4513	2025-06-24 19:48:53.49247-05
3656	4360	4513	2025-06-24 19:48:53.49247-05
3657	4361	4513	2025-06-24 19:48:53.49247-05
3658	4362	4513	2025-06-24 19:48:53.49247-05
3659	4363	4513	2025-06-24 19:48:53.49247-05
3660	4331	4513	2025-06-24 19:48:53.49247-05
3661	4332	4513	2025-06-24 19:48:53.49247-05
3662	4333	4513	2025-06-24 19:48:53.49247-05
3663	4334	4513	2025-06-24 19:48:53.49247-05
3664	4335	4513	2025-06-24 19:48:53.49247-05
3665	4336	4513	2025-06-24 19:48:53.49247-05
3666	4337	4513	2025-06-24 19:48:53.49247-05
3667	4338	4513	2025-06-24 19:48:53.49247-05
3668	4339	4513	2025-06-24 19:48:53.49247-05
3669	4340	4513	2025-06-24 19:48:53.49247-05
3670	4341	4513	2025-06-24 19:48:53.49247-05
3671	4342	4513	2025-06-24 19:48:53.49247-05
3672	4434	4514	2025-06-24 19:48:53.49247-05
3673	4430	4514	2025-06-24 19:48:53.49247-05
3674	4431	4514	2025-06-24 19:48:53.49247-05
3675	4432	4514	2025-06-24 19:48:53.49247-05
3676	4433	4514	2025-06-24 19:48:53.49247-05
3677	4260	4511	2025-06-24 19:48:53.49247-05
3678	4276	4511	2025-06-24 19:48:53.49247-05
3679	4292	4511	2025-06-24 19:48:53.49247-05
3680	4306	4511	2025-06-24 19:48:53.49247-05
3681	4325	4511	2025-06-24 19:48:53.49247-05
3682	4315	4511	2025-06-24 19:48:53.49247-05
3683	4316	4511	2025-06-24 19:48:53.49247-05
3684	4317	4511	2025-06-24 19:48:53.49247-05
3685	4318	4511	2025-06-24 19:48:53.49247-05
3686	4319	4511	2025-06-24 19:48:53.49247-05
3687	4320	4511	2025-06-24 19:48:53.49247-05
3688	4321	4511	2025-06-24 19:48:53.49247-05
3689	4261	4511	2025-06-24 19:48:53.49247-05
3690	4262	4511	2025-06-24 19:48:53.49247-05
3691	4263	4511	2025-06-24 19:48:53.49247-05
3692	4264	4511	2025-06-24 19:48:53.49247-05
3693	4265	4511	2025-06-24 19:48:53.49247-05
3694	4266	4511	2025-06-24 19:48:53.49247-05
3695	4267	4511	2025-06-24 19:48:53.49247-05
3696	4268	4511	2025-06-24 19:48:53.49247-05
3697	4269	4511	2025-06-24 19:48:53.49247-05
3698	4270	4511	2025-06-24 19:48:53.49247-05
3699	4271	4511	2025-06-24 19:48:53.49247-05
3700	4272	4511	2025-06-24 19:48:53.49247-05
3701	4273	4511	2025-06-24 19:48:53.49247-05
3702	4274	4511	2025-06-24 19:48:53.49247-05
3703	4275	4511	2025-06-24 19:48:53.49247-05
3704	4277	4511	2025-06-24 19:48:53.49247-05
3705	4278	4511	2025-06-24 19:48:53.49247-05
3706	4279	4511	2025-06-24 19:48:53.49247-05
3707	4280	4511	2025-06-24 19:48:53.49247-05
3708	4281	4511	2025-06-24 19:48:53.49247-05
3709	4282	4511	2025-06-24 19:48:53.49247-05
3710	4283	4511	2025-06-24 19:48:53.49247-05
3711	4284	4511	2025-06-24 19:48:53.49247-05
3712	4285	4511	2025-06-24 19:48:53.49247-05
3713	4286	4511	2025-06-24 19:48:53.49247-05
3714	4287	4511	2025-06-24 19:48:53.49247-05
3715	4288	4511	2025-06-24 19:48:53.49247-05
3716	4289	4511	2025-06-24 19:48:53.49247-05
3717	4290	4511	2025-06-24 19:48:53.49247-05
3718	4291	4511	2025-06-24 19:48:53.49247-05
3719	4296	4511	2025-06-24 19:48:53.49247-05
3720	4297	4511	2025-06-24 19:48:53.49247-05
3721	4298	4511	2025-06-24 19:48:53.49247-05
3722	4299	4511	2025-06-24 19:48:53.49247-05
3723	4300	4511	2025-06-24 19:48:53.49247-05
3724	4301	4511	2025-06-24 19:48:53.49247-05
3725	4302	4511	2025-06-24 19:48:53.49247-05
3726	4303	4511	2025-06-24 19:48:53.49247-05
3727	4304	4511	2025-06-24 19:48:53.49247-05
3728	4305	4511	2025-06-24 19:48:53.49247-05
\.


--
-- TOC entry 4166 (class 0 OID 46588)
-- Dependencies: 252
-- Data for Name: series_name_mappings; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.series_name_mappings (id, league_id, user_series_name, database_series_name, created_at, updated_at) FROM stdin;
18	CNSWPL	Division A	Series A	2025-06-21 18:05:51.480831	2025-06-21 18:05:51.480831
19	CNSWPL	Division B	Series B	2025-06-21 18:05:51.480831	2025-06-21 18:05:51.480831
20	CNSWPL	Division C	Series C	2025-06-21 18:05:51.480831	2025-06-21 18:05:51.480831
21	CNSWPL	Division D	Series D	2025-06-21 18:05:51.480831	2025-06-21 18:05:51.480831
22	CNSWPL	Division E	Series E	2025-06-21 18:05:51.480831	2025-06-21 18:05:51.480831
23	CNSWPL	Division F	Series F	2025-06-21 18:05:51.480831	2025-06-21 18:05:51.480831
24	CNSWPL	Division G	Series G	2025-06-21 18:05:51.480831	2025-06-21 18:05:51.480831
25	CNSWPL	Division H	Series H	2025-06-21 18:05:51.480831	2025-06-21 18:05:51.480831
26	CNSWPL	Division I	Series I	2025-06-21 18:05:51.480831	2025-06-21 18:05:51.480831
27	CNSWPL	Division J	Series J	2025-06-21 18:05:51.480831	2025-06-21 18:05:51.480831
28	CNSWPL	Division K	Series K	2025-06-21 18:05:51.480831	2025-06-21 18:05:51.480831
29	CNSWPL	Division SN	Series SN	2025-06-21 18:05:51.480831	2025-06-21 18:05:51.480831
30	NSTF	Series 1	S1	2025-06-21 18:05:51.480831	2025-06-21 18:05:51.480831
31	NSTF	Series 2A	S2A	2025-06-21 18:05:51.480831	2025-06-21 18:05:51.480831
32	NSTF	Series 2B	S2B	2025-06-21 18:05:51.480831	2025-06-21 18:05:51.480831
33	NSTF	Series 3	S3	2025-06-21 18:05:51.480831	2025-06-21 18:05:51.480831
34	NSTF	Series A	SA	2025-06-21 18:05:51.480831	2025-06-21 18:05:51.480831
37	CITA	Boys Division	Boys	2025-06-21 18:07:47.166286	2025-06-21 18:07:47.166286
38	CITA	Girls Division	Girls	2025-06-21 18:07:47.32469	2025-06-21 18:07:47.32469
1	CNSWPL	Division 1	S1	2025-06-21 18:05:51.480831	2025-06-21 18:15:58.485969
2	CNSWPL	Division 2	S2	2025-06-21 18:05:51.480831	2025-06-21 18:15:58.493112
3	CNSWPL	Division 3	S3	2025-06-21 18:05:51.480831	2025-06-21 18:15:58.499776
4	CNSWPL	Division 4	S4	2025-06-21 18:05:51.480831	2025-06-21 18:15:58.506087
5	CNSWPL	Division 5	S5	2025-06-21 18:05:51.480831	2025-06-21 18:15:58.511304
6	CNSWPL	Division 6	S6	2025-06-21 18:05:51.480831	2025-06-21 18:15:58.515219
7	CNSWPL	Division 7	S7	2025-06-21 18:05:51.480831	2025-06-21 18:15:58.51822
8	CNSWPL	Division 8	S8	2025-06-21 18:05:51.480831	2025-06-21 18:15:58.521328
9	CNSWPL	Division 9	S9	2025-06-21 18:05:51.480831	2025-06-21 18:15:58.524193
10	CNSWPL	Division 10	S10	2025-06-21 18:05:51.480831	2025-06-21 18:15:58.526832
11	CNSWPL	Division 11	S11	2025-06-21 18:05:51.480831	2025-06-21 18:15:58.529397
12	CNSWPL	Division 12	S12	2025-06-21 18:05:51.480831	2025-06-21 18:15:58.531768
13	CNSWPL	Division 13	S13	2025-06-21 18:05:51.480831	2025-06-21 18:15:58.53417
14	CNSWPL	Division 14	S14	2025-06-21 18:05:51.480831	2025-06-21 18:15:58.53659
15	CNSWPL	Division 15	S15	2025-06-21 18:05:51.480831	2025-06-21 18:15:58.539534
16	CNSWPL	Division 16	S16	2025-06-21 18:05:51.480831	2025-06-21 18:15:58.542068
17	CNSWPL	Division 17	S17	2025-06-21 18:05:51.480831	2025-06-21 18:15:58.544659
\.


--
-- TOC entry 4168 (class 0 OID 46594)
-- Dependencies: 254
-- Data for Name: series_stats; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.series_stats (id, series, team, points, matches_won, matches_lost, matches_tied, lines_won, lines_lost, lines_for, lines_ret, sets_won, sets_lost, games_won, games_lost, created_at, league_id, team_id) FROM stdin;
\.


--
-- TOC entry 4170 (class 0 OID 46601)
-- Dependencies: 256
-- Data for Name: team_format_mappings; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.team_format_mappings (id, league_id, user_input_format, database_series_format, mapping_type, description, is_active, created_at, updated_at) FROM stdin;
1	CNSWPL	Division 1	S1	series_mapping	Division format to short series format	t	2025-06-21 18:24:12.845913	2025-06-21 18:24:12.845913
2	CNSWPL	Division 2	S2	series_mapping	Division format to short series format	t	2025-06-21 18:24:12.845913	2025-06-21 18:24:12.845913
3	CNSWPL	Division 3	S3	series_mapping	Division format to short series format	t	2025-06-21 18:24:12.845913	2025-06-21 18:24:12.845913
4	CNSWPL	Division 4	S4	series_mapping	Division format to short series format	t	2025-06-21 18:24:12.845913	2025-06-21 18:24:12.845913
5	CNSWPL	Division 5	S5	series_mapping	Division format to short series format	t	2025-06-21 18:24:12.845913	2025-06-21 18:24:12.845913
6	CNSWPL	Division 6	S6	series_mapping	Division format to short series format	t	2025-06-21 18:24:12.845913	2025-06-21 18:24:12.845913
7	CNSWPL	Division 7	S7	series_mapping	Division format to short series format	t	2025-06-21 18:24:12.845913	2025-06-21 18:24:12.845913
8	CNSWPL	Division 8	S8	series_mapping	Division format to short series format	t	2025-06-21 18:24:12.845913	2025-06-21 18:24:12.845913
9	CNSWPL	Division 9	S9	series_mapping	Division format to short series format	t	2025-06-21 18:24:12.845913	2025-06-21 18:24:12.845913
10	CNSWPL	Division 10	S10	series_mapping	Division format to short series format	t	2025-06-21 18:24:12.845913	2025-06-21 18:24:12.845913
11	CNSWPL	Division 11	S11	series_mapping	Division format to short series format	t	2025-06-21 18:24:12.845913	2025-06-21 18:24:12.845913
12	CNSWPL	Division 12	S12	series_mapping	Division format to short series format	t	2025-06-21 18:24:12.845913	2025-06-21 18:24:12.845913
13	CNSWPL	Division 13	S13	series_mapping	Division format to short series format	t	2025-06-21 18:24:12.845913	2025-06-21 18:24:12.845913
14	CNSWPL	Division 14	S14	series_mapping	Division format to short series format	t	2025-06-21 18:24:12.845913	2025-06-21 18:24:12.845913
15	CNSWPL	Division 15	S15	series_mapping	Division format to short series format	t	2025-06-21 18:24:12.845913	2025-06-21 18:24:12.845913
16	CNSWPL	Division 16	S16	series_mapping	Division format to short series format	t	2025-06-21 18:24:12.845913	2025-06-21 18:24:12.845913
17	CNSWPL	Division 17	S17	series_mapping	Division format to short series format	t	2025-06-21 18:24:12.845913	2025-06-21 18:24:12.845913
18	CNSWPL	Series 1	S1	series_mapping	Long series format to short series format	t	2025-06-21 18:24:12.845913	2025-06-21 18:24:12.845913
19	CNSWPL	Series 2	S2	series_mapping	Long series format to short series format	t	2025-06-21 18:24:12.845913	2025-06-21 18:24:12.845913
20	CNSWPL	Series 3	S3	series_mapping	Long series format to short series format	t	2025-06-21 18:24:12.845913	2025-06-21 18:24:12.845913
21	CNSWPL	Series 4	S4	series_mapping	Long series format to short series format	t	2025-06-21 18:24:12.845913	2025-06-21 18:24:12.845913
22	CNSWPL	Series 5	S5	series_mapping	Long series format to short series format	t	2025-06-21 18:24:12.845913	2025-06-21 18:24:12.845913
23	CNSWPL	Series 6	S6	series_mapping	Long series format to short series format	t	2025-06-21 18:24:12.845913	2025-06-21 18:24:12.845913
24	CNSWPL	Series 7	S7	series_mapping	Long series format to short series format	t	2025-06-21 18:24:12.845913	2025-06-21 18:24:12.845913
25	CNSWPL	Series 8	S8	series_mapping	Long series format to short series format	t	2025-06-21 18:24:12.845913	2025-06-21 18:24:12.845913
26	CNSWPL	Series 9	S9	series_mapping	Long series format to short series format	t	2025-06-21 18:24:12.845913	2025-06-21 18:24:12.845913
27	CNSWPL	Series 10	S10	series_mapping	Long series format to short series format	t	2025-06-21 18:24:12.845913	2025-06-21 18:24:12.845913
28	CNSWPL	Series 11	S11	series_mapping	Long series format to short series format	t	2025-06-21 18:24:12.845913	2025-06-21 18:24:12.845913
29	CNSWPL	Series 12	S12	series_mapping	Long series format to short series format	t	2025-06-21 18:24:12.845913	2025-06-21 18:24:12.845913
30	CNSWPL	Series 13	S13	series_mapping	Long series format to short series format	t	2025-06-21 18:24:12.845913	2025-06-21 18:24:12.845913
31	CNSWPL	Series 14	S14	series_mapping	Long series format to short series format	t	2025-06-21 18:24:12.845913	2025-06-21 18:24:12.845913
32	CNSWPL	Series 15	S15	series_mapping	Long series format to short series format	t	2025-06-21 18:24:12.845913	2025-06-21 18:24:12.845913
33	CNSWPL	Series 16	S16	series_mapping	Long series format to short series format	t	2025-06-21 18:24:12.845913	2025-06-21 18:24:12.845913
34	CNSWPL	Series 17	S17	series_mapping	Long series format to short series format	t	2025-06-21 18:24:12.845913	2025-06-21 18:24:12.845913
35	CNSWPL	1	S1	series_mapping	Numeric only to short series format	t	2025-06-21 18:24:12.845913	2025-06-21 18:24:12.845913
36	CNSWPL	2	S2	series_mapping	Numeric only to short series format	t	2025-06-21 18:24:12.845913	2025-06-21 18:24:12.845913
37	CNSWPL	3	S3	series_mapping	Numeric only to short series format	t	2025-06-21 18:24:12.845913	2025-06-21 18:24:12.845913
38	CNSWPL	4	S4	series_mapping	Numeric only to short series format	t	2025-06-21 18:24:12.845913	2025-06-21 18:24:12.845913
39	CNSWPL	5	S5	series_mapping	Numeric only to short series format	t	2025-06-21 18:24:12.845913	2025-06-21 18:24:12.845913
40	CNSWPL	6	S6	series_mapping	Numeric only to short series format	t	2025-06-21 18:24:12.845913	2025-06-21 18:24:12.845913
41	CNSWPL	7	S7	series_mapping	Numeric only to short series format	t	2025-06-21 18:24:12.845913	2025-06-21 18:24:12.845913
42	CNSWPL	8	S8	series_mapping	Numeric only to short series format	t	2025-06-21 18:24:12.845913	2025-06-21 18:24:12.845913
43	CNSWPL	9	S9	series_mapping	Numeric only to short series format	t	2025-06-21 18:24:12.845913	2025-06-21 18:24:12.845913
44	CNSWPL	10	S10	series_mapping	Numeric only to short series format	t	2025-06-21 18:24:12.845913	2025-06-21 18:24:12.845913
45	CNSWPL	11	S11	series_mapping	Numeric only to short series format	t	2025-06-21 18:24:12.845913	2025-06-21 18:24:12.845913
46	CNSWPL	12	S12	series_mapping	Numeric only to short series format	t	2025-06-21 18:24:12.845913	2025-06-21 18:24:12.845913
47	CNSWPL	13	S13	series_mapping	Numeric only to short series format	t	2025-06-21 18:24:12.845913	2025-06-21 18:24:12.845913
48	CNSWPL	14	S14	series_mapping	Numeric only to short series format	t	2025-06-21 18:24:12.845913	2025-06-21 18:24:12.845913
49	CNSWPL	15	S15	series_mapping	Numeric only to short series format	t	2025-06-21 18:24:12.845913	2025-06-21 18:24:12.845913
50	CNSWPL	16	S16	series_mapping	Numeric only to short series format	t	2025-06-21 18:24:12.845913	2025-06-21 18:24:12.845913
51	CNSWPL	17	S17	series_mapping	Numeric only to short series format	t	2025-06-21 18:24:12.845913	2025-06-21 18:24:12.845913
52	CNSWPL	S1	S1	series_mapping	Direct match	t	2025-06-21 18:24:12.845913	2025-06-21 18:24:12.845913
53	CNSWPL	S2	S2	series_mapping	Direct match	t	2025-06-21 18:24:12.845913	2025-06-21 18:24:12.845913
54	CNSWPL	S3	S3	series_mapping	Direct match	t	2025-06-21 18:24:12.845913	2025-06-21 18:24:12.845913
55	CNSWPL	S4	S4	series_mapping	Direct match	t	2025-06-21 18:24:12.845913	2025-06-21 18:24:12.845913
56	CNSWPL	S5	S5	series_mapping	Direct match	t	2025-06-21 18:24:12.845913	2025-06-21 18:24:12.845913
57	CNSWPL	S6	S6	series_mapping	Direct match	t	2025-06-21 18:24:12.845913	2025-06-21 18:24:12.845913
58	CNSWPL	S7	S7	series_mapping	Direct match	t	2025-06-21 18:24:12.845913	2025-06-21 18:24:12.845913
59	CNSWPL	S8	S8	series_mapping	Direct match	t	2025-06-21 18:24:12.845913	2025-06-21 18:24:12.845913
60	CNSWPL	S9	S9	series_mapping	Direct match	t	2025-06-21 18:24:12.845913	2025-06-21 18:24:12.845913
61	CNSWPL	S10	S10	series_mapping	Direct match	t	2025-06-21 18:24:12.845913	2025-06-21 18:24:12.845913
62	CNSWPL	S11	S11	series_mapping	Direct match	t	2025-06-21 18:24:12.845913	2025-06-21 18:24:12.845913
63	CNSWPL	S12	S12	series_mapping	Direct match	t	2025-06-21 18:24:12.845913	2025-06-21 18:24:12.845913
64	CNSWPL	S13	S13	series_mapping	Direct match	t	2025-06-21 18:24:12.845913	2025-06-21 18:24:12.845913
65	CNSWPL	S14	S14	series_mapping	Direct match	t	2025-06-21 18:24:12.845913	2025-06-21 18:24:12.845913
66	CNSWPL	S15	S15	series_mapping	Direct match	t	2025-06-21 18:24:12.845913	2025-06-21 18:24:12.845913
67	CNSWPL	S16	S16	series_mapping	Direct match	t	2025-06-21 18:24:12.845913	2025-06-21 18:24:12.845913
68	CNSWPL	S17	S17	series_mapping	Direct match	t	2025-06-21 18:24:12.845913	2025-06-21 18:24:12.845913
69	CNSWPL	Division I	SI	series_mapping	Division I to SI format	t	2025-06-21 18:24:12.845913	2025-06-21 18:24:12.845913
70	CNSWPL	Series I	SI	series_mapping	Series I to SI format	t	2025-06-21 18:24:12.845913	2025-06-21 18:24:12.845913
71	CNSWPL	I	SI	series_mapping	Letter I to SI format	t	2025-06-21 18:24:12.845913	2025-06-21 18:24:12.845913
72	CNSWPL	SI	SI	series_mapping	Direct match	t	2025-06-21 18:24:12.845913	2025-06-21 18:24:12.845913
73	NSTF	Series 1	S1	series_mapping	Long series format to short format	t	2025-06-21 18:24:12.845913	2025-06-21 18:24:12.845913
74	NSTF	Series 2A	S2A	series_mapping	Long series format to short format	t	2025-06-21 18:24:12.845913	2025-06-21 18:24:12.845913
75	NSTF	Series 2B	S2B	series_mapping	Long series format to short format	t	2025-06-21 18:24:12.845913	2025-06-21 18:24:12.845913
76	NSTF	Series 3	S3	series_mapping	Long series format to short format	t	2025-06-21 18:24:12.845913	2025-06-21 18:24:12.845913
77	NSTF	Series A	SA	series_mapping	Long series format to short format	t	2025-06-21 18:24:12.845913	2025-06-21 18:24:12.845913
78	NSTF	Division 1	S1	series_mapping	Division format to short format	t	2025-06-21 18:24:12.845913	2025-06-21 18:24:12.845913
79	NSTF	Division 2A	S2A	series_mapping	Division format to short format	t	2025-06-21 18:24:12.845913	2025-06-21 18:24:12.845913
80	NSTF	Division 2B	S2B	series_mapping	Division format to short format	t	2025-06-21 18:24:12.845913	2025-06-21 18:24:12.845913
81	NSTF	Division 3	S3	series_mapping	Division format to short format	t	2025-06-21 18:24:12.845913	2025-06-21 18:24:12.845913
82	NSTF	Division A	SA	series_mapping	Division format to short format	t	2025-06-21 18:24:12.845913	2025-06-21 18:24:12.845913
83	NSTF	1	S1	series_mapping	Numeric only to short format	t	2025-06-21 18:24:12.845913	2025-06-21 18:24:12.845913
84	NSTF	2A	S2A	series_mapping	Alphanumeric to short format	t	2025-06-21 18:24:12.845913	2025-06-21 18:24:12.845913
85	NSTF	2B	S2B	series_mapping	Alphanumeric to short format	t	2025-06-21 18:24:12.845913	2025-06-21 18:24:12.845913
86	NSTF	3	S3	series_mapping	Numeric only to short format	t	2025-06-21 18:24:12.845913	2025-06-21 18:24:12.845913
87	NSTF	A	SA	series_mapping	Letter only to short format	t	2025-06-21 18:24:12.845913	2025-06-21 18:24:12.845913
88	NSTF	S1	S1	series_mapping	Direct match	t	2025-06-21 18:24:12.845913	2025-06-21 18:24:12.845913
89	NSTF	S2A	S2A	series_mapping	Direct match	t	2025-06-21 18:24:12.845913	2025-06-21 18:24:12.845913
90	NSTF	S2B	S2B	series_mapping	Direct match	t	2025-06-21 18:24:12.845913	2025-06-21 18:24:12.845913
91	NSTF	S3	S3	series_mapping	Direct match	t	2025-06-21 18:24:12.845913	2025-06-21 18:24:12.845913
92	NSTF	SA	SA	series_mapping	Direct match	t	2025-06-21 18:24:12.845913	2025-06-21 18:24:12.845913
93	APTA_CHICAGO	Chicago 1	Chicago 1	series_mapping	Direct match	t	2025-06-21 18:24:12.845913	2025-06-21 18:24:12.845913
94	APTA_CHICAGO	Chicago 2	Chicago 2	series_mapping	Direct match	t	2025-06-21 18:24:12.845913	2025-06-21 18:24:12.845913
95	APTA_CHICAGO	Chicago 3	Chicago 3	series_mapping	Direct match	t	2025-06-21 18:24:12.845913	2025-06-21 18:24:12.845913
96	APTA_CHICAGO	Chicago 4	Chicago 4	series_mapping	Direct match	t	2025-06-21 18:24:12.845913	2025-06-21 18:24:12.845913
97	APTA_CHICAGO	Chicago 5	Chicago 5	series_mapping	Direct match	t	2025-06-21 18:24:12.845913	2025-06-21 18:24:12.845913
98	APTA_CHICAGO	Chicago 6	Chicago 6	series_mapping	Direct match	t	2025-06-21 18:24:12.845913	2025-06-21 18:24:12.845913
99	APTA_CHICAGO	Chicago 7	Chicago 7	series_mapping	Direct match	t	2025-06-21 18:24:12.845913	2025-06-21 18:24:12.845913
100	APTA_CHICAGO	Chicago 8	Chicago 8	series_mapping	Direct match	t	2025-06-21 18:24:12.845913	2025-06-21 18:24:12.845913
101	APTA_CHICAGO	Chicago 9	Chicago 9	series_mapping	Direct match	t	2025-06-21 18:24:12.845913	2025-06-21 18:24:12.845913
102	APTA_CHICAGO	Chicago 10	Chicago 10	series_mapping	Direct match	t	2025-06-21 18:24:12.845913	2025-06-21 18:24:12.845913
103	APTA_CHICAGO	Chicago 11	Chicago 11	series_mapping	Direct match	t	2025-06-21 18:24:12.845913	2025-06-21 18:24:12.845913
104	APTA_CHICAGO	Chicago 12	Chicago 12	series_mapping	Direct match	t	2025-06-21 18:24:12.845913	2025-06-21 18:24:12.845913
105	APTA_CHICAGO	Chicago 13	Chicago 13	series_mapping	Direct match	t	2025-06-21 18:24:12.845913	2025-06-21 18:24:12.845913
106	APTA_CHICAGO	Chicago 14	Chicago 14	series_mapping	Direct match	t	2025-06-21 18:24:12.845913	2025-06-21 18:24:12.845913
107	APTA_CHICAGO	Chicago 15	Chicago 15	series_mapping	Direct match	t	2025-06-21 18:24:12.845913	2025-06-21 18:24:12.845913
108	APTA_CHICAGO	Chicago 16	Chicago 16	series_mapping	Direct match	t	2025-06-21 18:24:12.845913	2025-06-21 18:24:12.845913
109	APTA_CHICAGO	Chicago 17	Chicago 17	series_mapping	Direct match	t	2025-06-21 18:24:12.845913	2025-06-21 18:24:12.845913
110	APTA_CHICAGO	Chicago 18	Chicago 18	series_mapping	Direct match	t	2025-06-21 18:24:12.845913	2025-06-21 18:24:12.845913
111	APTA_CHICAGO	Chicago 19	Chicago 19	series_mapping	Direct match	t	2025-06-21 18:24:12.845913	2025-06-21 18:24:12.845913
112	APTA_CHICAGO	Chicago 20	Chicago 20	series_mapping	Direct match	t	2025-06-21 18:24:12.845913	2025-06-21 18:24:12.845913
113	APTA_CHICAGO	Division 6	Division 6	series_mapping	Direct match	t	2025-06-21 18:24:12.845913	2025-06-21 18:24:12.845913
114	APTA_CHICAGO	Division 7	Division 7	series_mapping	Direct match	t	2025-06-21 18:24:12.845913	2025-06-21 18:24:12.845913
115	APTA_CHICAGO	Division 9	Division 9	series_mapping	Direct match	t	2025-06-21 18:24:12.845913	2025-06-21 18:24:12.845913
116	APTA_CHICAGO	Division 11	Division 11	series_mapping	Direct match	t	2025-06-21 18:24:12.845913	2025-06-21 18:24:12.845913
117	APTA_CHICAGO	Division 13	Division 13	series_mapping	Direct match	t	2025-06-21 18:24:12.845913	2025-06-21 18:24:12.845913
118	APTA_CHICAGO	Division 15	Division 15	series_mapping	Direct match	t	2025-06-21 18:24:12.845913	2025-06-21 18:24:12.845913
119	APTA_CHICAGO	Division 17	Division 17	series_mapping	Direct match	t	2025-06-21 18:24:12.845913	2025-06-21 18:24:12.845913
120	APTA_CHICAGO	Division 19	Division 19	series_mapping	Direct match	t	2025-06-21 18:24:12.845913	2025-06-21 18:24:12.845913
121	APTA_CHICAGO	1	Chicago 1	series_mapping	Numeric to Chicago format	t	2025-06-21 18:24:12.845913	2025-06-21 18:24:12.845913
122	APTA_CHICAGO	2	Chicago 2	series_mapping	Numeric to Chicago format	t	2025-06-21 18:24:12.845913	2025-06-21 18:24:12.845913
123	APTA_CHICAGO	3	Chicago 3	series_mapping	Numeric to Chicago format	t	2025-06-21 18:24:12.845913	2025-06-21 18:24:12.845913
124	APTA_CHICAGO	4	Chicago 4	series_mapping	Numeric to Chicago format	t	2025-06-21 18:24:12.845913	2025-06-21 18:24:12.845913
125	APTA_CHICAGO	5	Chicago 5	series_mapping	Numeric to Chicago format	t	2025-06-21 18:24:12.845913	2025-06-21 18:24:12.845913
126	APTA_CHICAGO	6	Chicago 6	series_mapping	Numeric to Chicago format	t	2025-06-21 18:24:12.845913	2025-06-21 18:24:12.845913
127	APTA_CHICAGO	7	Chicago 7	series_mapping	Numeric to Chicago format	t	2025-06-21 18:24:12.845913	2025-06-21 18:24:12.845913
128	APTA_CHICAGO	8	Chicago 8	series_mapping	Numeric to Chicago format	t	2025-06-21 18:24:12.845913	2025-06-21 18:24:12.845913
129	APTA_CHICAGO	9	Chicago 9	series_mapping	Numeric to Chicago format	t	2025-06-21 18:24:12.845913	2025-06-21 18:24:12.845913
130	APTA_CHICAGO	10	Chicago 10	series_mapping	Numeric to Chicago format	t	2025-06-21 18:24:12.845913	2025-06-21 18:24:12.845913
131	APTA_CHICAGO	11	Chicago 11	series_mapping	Numeric to Chicago format	t	2025-06-21 18:24:12.845913	2025-06-21 18:24:12.845913
132	APTA_CHICAGO	12	Chicago 12	series_mapping	Numeric to Chicago format	t	2025-06-21 18:24:12.845913	2025-06-21 18:24:12.845913
133	APTA_CHICAGO	13	Chicago 13	series_mapping	Numeric to Chicago format	t	2025-06-21 18:24:12.845913	2025-06-21 18:24:12.845913
134	APTA_CHICAGO	14	Chicago 14	series_mapping	Numeric to Chicago format	t	2025-06-21 18:24:12.845913	2025-06-21 18:24:12.845913
135	APTA_CHICAGO	15	Chicago 15	series_mapping	Numeric to Chicago format	t	2025-06-21 18:24:12.845913	2025-06-21 18:24:12.845913
136	APTA_CHICAGO	16	Chicago 16	series_mapping	Numeric to Chicago format	t	2025-06-21 18:24:12.845913	2025-06-21 18:24:12.845913
137	APTA_CHICAGO	17	Chicago 17	series_mapping	Numeric to Chicago format	t	2025-06-21 18:24:12.845913	2025-06-21 18:24:12.845913
138	APTA_CHICAGO	18	Chicago 18	series_mapping	Numeric to Chicago format	t	2025-06-21 18:24:12.845913	2025-06-21 18:24:12.845913
139	APTA_CHICAGO	19	Chicago 19	series_mapping	Numeric to Chicago format	t	2025-06-21 18:24:12.845913	2025-06-21 18:24:12.845913
140	APTA_CHICAGO	20	Chicago 20	series_mapping	Numeric to Chicago format	t	2025-06-21 18:24:12.845913	2025-06-21 18:24:12.845913
141	APTA_CHICAGO	S7 SW	S7 SW	series_mapping	Direct match	t	2025-06-21 18:24:12.845913	2025-06-21 18:24:12.845913
142	APTA_CHICAGO	S9 SW	S9 SW	series_mapping	Direct match	t	2025-06-21 18:24:12.845913	2025-06-21 18:24:12.845913
143	APTA_CHICAGO	S11 SW	S11 SW	series_mapping	Direct match	t	2025-06-21 18:24:12.845913	2025-06-21 18:24:12.845913
144	APTA_CHICAGO	S13 SW	S13 SW	series_mapping	Direct match	t	2025-06-21 18:24:12.845913	2025-06-21 18:24:12.845913
145	APTA_CHICAGO	S15 SW	S15 SW	series_mapping	Direct match	t	2025-06-21 18:24:12.845913	2025-06-21 18:24:12.845913
146	APTA_CHICAGO	S17 SW	S17 SW	series_mapping	Direct match	t	2025-06-21 18:24:12.845913	2025-06-21 18:24:12.845913
147	APTA_CHICAGO	S19 SW	S19 SW	series_mapping	Direct match	t	2025-06-21 18:24:12.845913	2025-06-21 18:24:12.845913
148	APTA_CHICAGO	S21 SW	S21 SW	series_mapping	Direct match	t	2025-06-21 18:24:12.845913	2025-06-21 18:24:12.845913
149	APTA_CHICAGO	S23 SW	S23 SW	series_mapping	Direct match	t	2025-06-21 18:24:12.845913	2025-06-21 18:24:12.845913
150	APTA_CHICAGO	S25 SW	S25 SW	series_mapping	Direct match	t	2025-06-21 18:24:12.845913	2025-06-21 18:24:12.845913
151	APTA_CHICAGO	S27 SW	S27 SW	series_mapping	Direct match	t	2025-06-21 18:24:12.845913	2025-06-21 18:24:12.845913
152	APTA_CHICAGO	S29 SW	S29 SW	series_mapping	Direct match	t	2025-06-21 18:24:12.845913	2025-06-21 18:24:12.845913
153	CITA	Boys	SBoys	series_mapping	Boys division mapping	t	2025-06-21 18:24:12.845913	2025-06-21 18:24:12.845913
154	CITA	Boys Division	SBoys	series_mapping	Boys division mapping	t	2025-06-21 18:24:12.845913	2025-06-21 18:24:12.845913
155	CITA	Girls	SGirls	series_mapping	Girls division mapping	t	2025-06-21 18:24:12.845913	2025-06-21 18:24:12.845913
156	CITA	Girls Division	SGirls	series_mapping	Girls division mapping	t	2025-06-21 18:24:12.845913	2025-06-21 18:24:12.845913
157	CITA	SBoys	SBoys	series_mapping	Direct match	t	2025-06-21 18:24:12.845913	2025-06-21 18:24:12.845913
158	CITA	S3.0 & Under Thur	S3.0 & Under Thur	series_mapping	Direct match	t	2025-06-21 18:24:12.845913	2025-06-21 18:24:12.845913
159	CITA	S3.0 - 3.5 Singles Thur	S3.0 - 3.5 Singles Thur	series_mapping	Direct match	t	2025-06-21 18:24:12.845913	2025-06-21 18:24:12.845913
160	CITA	S3.5 & Under Sat	S3.5 & Under Sat	series_mapping	Direct match	t	2025-06-21 18:24:12.845913	2025-06-21 18:24:12.845913
161	CITA	S3.5 & Under Wed	S3.5 & Under Wed	series_mapping	Direct match	t	2025-06-21 18:24:12.845913	2025-06-21 18:24:12.845913
162	CITA	S4.0 & Under Fri	S4.0 & Under Fri	series_mapping	Direct match	t	2025-06-21 18:24:12.845913	2025-06-21 18:24:12.845913
163	CITA	S4.0 & Under Sat	S4.0 & Under Sat	series_mapping	Direct match	t	2025-06-21 18:24:12.845913	2025-06-21 18:24:12.845913
164	CITA	S4.0 & Under Wed	S4.0 & Under Wed	series_mapping	Direct match	t	2025-06-21 18:24:12.845913	2025-06-21 18:24:12.845913
165	CITA	S4.0 - 4.5 Singles Thur	S4.0 - 4.5 Singles Thur	series_mapping	Direct match	t	2025-06-21 18:24:12.845913	2025-06-21 18:24:12.845913
166	CITA	S4.0 Singles Sun	S4.0 Singles Sun	series_mapping	Direct match	t	2025-06-21 18:24:12.845913	2025-06-21 18:24:12.845913
167	CITA	S4.5 & Under Fri	S4.5 & Under Fri	series_mapping	Direct match	t	2025-06-21 18:24:12.845913	2025-06-21 18:24:12.845913
168	CITA	S4.5 & Under Sat	S4.5 & Under Sat	series_mapping	Direct match	t	2025-06-21 18:24:12.845913	2025-06-21 18:24:12.845913
169	CITA	S4.5 Singles Sun	S4.5 Singles Sun	series_mapping	Direct match	t	2025-06-21 18:24:12.845913	2025-06-21 18:24:12.845913
170	CITA	SOpen Fri	SOpen Fri	series_mapping	Direct match	t	2025-06-21 18:24:12.845913	2025-06-21 18:24:12.845913
198	APTA_CHICAGO	Midtown - Chicago 2	Midtown - Chicago 1	team_mapping	Auto-mapped: 80.0% similarity, 348 matches	t	2025-06-23 18:04:13.966586	2025-06-23 18:04:13.966586
199	APTA_CHICAGO	Midtown - Chicago	Midtown - Chicago - 10	team_mapping	Auto-mapped: 70.0% similarity, 215 matches	t	2025-06-23 18:04:13.976609	2025-06-23 18:04:13.976609
200	APTA_CHICAGO	Midtown - Bannockburn 2	Midtown - Bannockburn 1	team_mapping	Auto-mapped: 80.0% similarity, 84 matches	t	2025-06-23 18:04:13.983179	2025-06-23 18:04:13.983179
201	APTA_CHICAGO	Sunset Ridge 5b	Sunset Ridge 5a	team_mapping	Auto-mapped: 100.0% similarity, 36 matches	t	2025-06-23 18:04:13.988936	2025-06-23 18:04:13.988936
209	APTA_CHICAGO	Wilmette S1 T2	Wilmette PD I - 2	team_mapping	Auto-mapped: 80.0% similarity, 14 matches	t	2025-06-23 18:04:14.029121	2025-06-23 18:04:14.029121
210	APTA_CHICAGO	Lake Forest S1	Lake Forest S2B	team_mapping	Auto-mapped: 80.0% similarity, 10 matches	t	2025-06-23 18:04:14.033085	2025-06-23 18:04:14.033085
\.


--
-- TOC entry 4172 (class 0 OID 46611)
-- Dependencies: 258
-- Data for Name: teams; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.teams (id, club_id, series_id, league_id, team_name, external_team_id, is_active, created_at, updated_at, team_alias) FROM stdin;
13331	4567	4371	4513	Barrington Hills 10	\N	t	2025-06-24 19:48:53.499999-05	2025-06-24 19:48:53.499999-05	S10
13332	4567	4372	4513	Barrington Hills 11	\N	t	2025-06-24 19:48:53.499999-05	2025-06-24 19:48:53.499999-05	S11
13333	4567	4377	4513	Barrington Hills 14	\N	t	2025-06-24 19:48:53.499999-05	2025-06-24 19:48:53.499999-05	S14
13334	4568	4262	4511	Barrington Hills CC - 11	\N	t	2025-06-24 19:48:53.499999-05	2025-06-24 19:48:53.499999-05	Series 11
13335	4568	4332	4511	Barrington Hills CC - 11 (Division 11)	\N	t	2025-06-24 19:48:53.499999-05	2025-06-24 19:48:53.499999-05	Series 11 (Division 11)
13336	4568	4278	4511	Barrington Hills CC - 21	\N	t	2025-06-24 19:48:53.499999-05	2025-06-24 19:48:53.499999-05	Series 21
13337	4568	4287	4511	Barrington Hills CC - 27	\N	t	2025-06-24 19:48:53.499999-05	2025-06-24 19:48:53.499999-05	Series 27
13338	4568	4304	4511	Barrington Hills CC - 38	\N	t	2025-06-24 19:48:53.499999-05	2025-06-24 19:48:53.499999-05	Series 38
13339	4569	4377	4513	Biltmore 14a	\N	t	2025-06-24 19:48:53.499999-05	2025-06-24 19:48:53.499999-05	S14
13340	4569	4411	4513	Biltmore 8	\N	t	2025-06-24 19:48:53.499999-05	2025-06-24 19:48:53.499999-05	S8
13341	4570	4274	4511	Biltmore CC - 19	\N	t	2025-06-24 19:48:53.499999-05	2025-06-24 19:48:53.499999-05	Series 19
13342	4570	4343	4511	Biltmore CC - 19 (Division 19)	\N	t	2025-06-24 19:48:53.499999-05	2025-06-24 19:48:53.499999-05	Series 19 (Division 19)
13343	4570	4278	4511	Biltmore CC - 21	\N	t	2025-06-24 19:48:53.499999-05	2025-06-24 19:48:53.499999-05	Series 21
13344	4570	4290	4511	Biltmore CC - 29	\N	t	2025-06-24 19:48:53.499999-05	2025-06-24 19:48:53.499999-05	Series 29
13345	4570	4303	4511	Biltmore CC - 37	\N	t	2025-06-24 19:48:53.499999-05	2025-06-24 19:48:53.499999-05	Series 37
13346	4571	4262	4511	Birchwood - 11	\N	t	2025-06-24 19:48:53.499999-05	2025-06-24 19:48:53.499999-05	Series 11
13347	4571	4332	4511	Birchwood - 11 (Division 11)	\N	t	2025-06-24 19:48:53.499999-05	2025-06-24 19:48:53.499999-05	Series 11 (Division 11)
13348	4571	4265	4511	Birchwood - 13	\N	t	2025-06-24 19:48:53.499999-05	2025-06-24 19:48:53.499999-05	Series 13
13349	4571	4334	4511	Birchwood - 13 (Division 13)	\N	t	2025-06-24 19:48:53.499999-05	2025-06-24 19:48:53.499999-05	Series 13 (Division 13)
13350	4571	4267	4511	Birchwood - 14	\N	t	2025-06-24 19:48:53.499999-05	2025-06-24 19:48:53.499999-05	Series 14
13351	4571	4273	4511	Birchwood - 18	\N	t	2025-06-24 19:48:53.499999-05	2025-06-24 19:48:53.499999-05	Series 18
13352	4571	4276	4511	Birchwood - 2	\N	t	2025-06-24 19:48:53.499999-05	2025-06-24 19:48:53.499999-05	Series 2
13353	4571	4280	4511	Birchwood - 22	\N	t	2025-06-24 19:48:53.499999-05	2025-06-24 19:48:53.499999-05	Series 22
13354	4571	4283	4511	Birchwood - 24	\N	t	2025-06-24 19:48:53.499999-05	2025-06-24 19:48:53.499999-05	Series 24
13355	4571	4286	4511	Birchwood - 26	\N	t	2025-06-24 19:48:53.499999-05	2025-06-24 19:48:53.499999-05	Series 26
13356	4571	4300	4511	Birchwood - 34	\N	t	2025-06-24 19:48:53.499999-05	2025-06-24 19:48:53.499999-05	Series 34
13357	4571	4304	4511	Birchwood - 38	\N	t	2025-06-24 19:48:53.499999-05	2025-06-24 19:48:53.499999-05	Series 38
13358	4571	4306	4511	Birchwood - 4	\N	t	2025-06-24 19:48:53.499999-05	2025-06-24 19:48:53.499999-05	Series 4
13359	4571	4316	4511	Birchwood - 6	\N	t	2025-06-24 19:48:53.499999-05	2025-06-24 19:48:53.499999-05	Series 6
13360	4571	4358	4511	Birchwood - 6 (Division 6)	\N	t	2025-06-24 19:48:53.499999-05	2025-06-24 19:48:53.499999-05	Series 6 (Division 6)
13361	4571	4370	4513	Birchwood 1	\N	t	2025-06-24 19:48:53.499999-05	2025-06-24 19:48:53.499999-05	S1
13362	4571	4370	4514	Birchwood S1	\N	t	2025-06-24 19:48:53.499999-05	2025-06-24 19:48:53.499999-05	Series 1
13363	4571	4372	4513	Birchwood 11	\N	t	2025-06-24 19:48:53.499999-05	2025-06-24 19:48:53.499999-05	S11
13364	4571	4374	4513	Birchwood 12	\N	t	2025-06-24 19:48:53.499999-05	2025-06-24 19:48:53.499999-05	S12
13365	4571	4375	4513	Birchwood 13	\N	t	2025-06-24 19:48:53.499999-05	2025-06-24 19:48:53.499999-05	S13
13366	4571	4378	4513	Birchwood 15	\N	t	2025-06-24 19:48:53.499999-05	2025-06-24 19:48:53.499999-05	S15
13367	4571	4384	4513	Birchwood 2	\N	t	2025-06-24 19:48:53.499999-05	2025-06-24 19:48:53.499999-05	S2
13368	4571	4391	4514	Birchwood S2B	\N	t	2025-06-24 19:48:53.499999-05	2025-06-24 19:48:53.499999-05	Series 2B
13369	4571	4392	4514	Birchwood S3	\N	t	2025-06-24 19:48:53.499999-05	2025-06-24 19:48:53.499999-05	Series 3
13370	4571	4407	4513	Birchwood 5	\N	t	2025-06-24 19:48:53.499999-05	2025-06-24 19:48:53.499999-05	S5
13371	4571	4409	4513	Birchwood 7	\N	t	2025-06-24 19:48:53.499999-05	2025-06-24 19:48:53.499999-05	S7
13372	4571	4412	4513	Birchwood 9	\N	t	2025-06-24 19:48:53.499999-05	2025-06-24 19:48:53.499999-05	S9
13373	4572	4265	4511	Briarwood - 13	\N	t	2025-06-24 19:48:53.499999-05	2025-06-24 19:48:53.499999-05	Series 13
13374	4572	4334	4511	Briarwood - 13 (Division 13)	\N	t	2025-06-24 19:48:53.499999-05	2025-06-24 19:48:53.499999-05	Series 13 (Division 13)
13375	4572	4267	4511	Briarwood - 14	\N	t	2025-06-24 19:48:53.499999-05	2025-06-24 19:48:53.499999-05	Series 14
13376	4572	4277	4511	Briarwood - 20	\N	t	2025-06-24 19:48:53.499999-05	2025-06-24 19:48:53.499999-05	Series 20
13377	4572	4289	4511	Briarwood - 28	\N	t	2025-06-24 19:48:53.499999-05	2025-06-24 19:48:53.499999-05	Series 28
13378	4572	4302	4511	Briarwood - 36	\N	t	2025-06-24 19:48:53.499999-05	2025-06-24 19:48:53.499999-05	Series 36
13379	4572	4316	4511	Briarwood - 6	\N	t	2025-06-24 19:48:53.499999-05	2025-06-24 19:48:53.499999-05	Series 6
13380	4572	4358	4511	Briarwood - 6 (Division 6)	\N	t	2025-06-24 19:48:53.499999-05	2025-06-24 19:48:53.499999-05	Series 6 (Division 6)
13381	4572	4372	4513	Briarwood 11	\N	t	2025-06-24 19:48:53.499999-05	2025-06-24 19:48:53.499999-05	S11
13382	4572	4375	4513	Briarwood 13	\N	t	2025-06-24 19:48:53.499999-05	2025-06-24 19:48:53.499999-05	S13
13383	4572	4380	4513	Briarwood 16	\N	t	2025-06-24 19:48:53.499999-05	2025-06-24 19:48:53.499999-05	S16
13384	4572	4408	4513	Briarwood 6	\N	t	2025-06-24 19:48:53.499999-05	2025-06-24 19:48:53.499999-05	S6
13385	4573	4265	4511	Bryn Mawr - 13	\N	t	2025-06-24 19:48:53.499999-05	2025-06-24 19:48:53.499999-05	Series 13
13386	4573	4334	4511	Bryn Mawr - 13 (Division 13)	\N	t	2025-06-24 19:48:53.499999-05	2025-06-24 19:48:53.499999-05	Series 13 (Division 13)
13387	4573	4287	4511	Bryn Mawr - 27	\N	t	2025-06-24 19:48:53.499999-05	2025-06-24 19:48:53.499999-05	Series 27
13388	4573	4301	4511	Bryn Mawr - 35	\N	t	2025-06-24 19:48:53.499999-05	2025-06-24 19:48:53.499999-05	Series 35
13389	4573	4315	4511	Bryn Mawr - 5	\N	t	2025-06-24 19:48:53.499999-05	2025-06-24 19:48:53.499999-05	Series 5
13390	4574	4374	4513	Bryn Mawr CC 12	\N	t	2025-06-24 19:48:53.499999-05	2025-06-24 19:48:53.499999-05	S12
13391	4574	4378	4513	Bryn Mawr CC 15	\N	t	2025-06-24 19:48:53.499999-05	2025-06-24 19:48:53.499999-05	S15
13392	4575	4379	4511	Butterfield - 15 SW	\N	t	2025-06-24 19:48:53.499999-05	2025-06-24 19:48:53.499999-05	Series 15 SW
13393	4575	4383	4511	Butterfield - 19 SW	\N	t	2025-06-24 19:48:53.499999-05	2025-06-24 19:48:53.499999-05	Series 19 SW
13394	4575	4386	4511	Butterfield - 23 SW	\N	t	2025-06-24 19:48:53.499999-05	2025-06-24 19:48:53.499999-05	Series 23 SW
13395	4575	4388	4511	Butterfield - 27 SW	\N	t	2025-06-24 19:48:53.499999-05	2025-06-24 19:48:53.499999-05	Series 27 SW
13396	4575	4392	4513	Butterfield 3	\N	t	2025-06-24 19:48:53.499999-05	2025-06-24 19:48:53.499999-05	S3
13397	4575	4410	4511	Butterfield - 7 SW	\N	t	2025-06-24 19:48:53.499999-05	2025-06-24 19:48:53.499999-05	Series 7 SW
13398	4576	4373	4511	Chicago Highlands - 11 SW	\N	t	2025-06-24 19:48:53.499999-05	2025-06-24 19:48:53.499999-05	Series 11 SW
13399	4576	4379	4511	Chicago Highlands - 15 SW	\N	t	2025-06-24 19:48:53.499999-05	2025-06-24 19:48:53.499999-05	Series 15 SW
13400	4576	4382	4511	Chicago Highlands - 17 SW	\N	t	2025-06-24 19:48:53.499999-05	2025-06-24 19:48:53.499999-05	Series 17 SW
13401	4576	4383	4511	Chicago Highlands - 19 SW	\N	t	2025-06-24 19:48:53.499999-05	2025-06-24 19:48:53.499999-05	Series 19 SW
13402	4576	4386	4511	Chicago Highlands - 23 SW	\N	t	2025-06-24 19:48:53.499999-05	2025-06-24 19:48:53.499999-05	Series 23 SW
13403	4576	4387	4511	Chicago Highlands - 25 SW	\N	t	2025-06-24 19:48:53.499999-05	2025-06-24 19:48:53.499999-05	Series 25 SW
13404	4576	4388	4511	Chicago Highlands - 27 SW	\N	t	2025-06-24 19:48:53.499999-05	2025-06-24 19:48:53.499999-05	Series 27 SW
13405	4577	4382	4511	Dunham Woods - 17 SW	\N	t	2025-06-24 19:48:53.499999-05	2025-06-24 19:48:53.499999-05	Series 17 SW
13406	4577	4385	4511	Dunham Woods - 21 SW	\N	t	2025-06-24 19:48:53.499999-05	2025-06-24 19:48:53.499999-05	Series 21 SW
13407	4577	4389	4511	Dunham Woods - 29 SW	\N	t	2025-06-24 19:48:53.499999-05	2025-06-24 19:48:53.499999-05	Series 29 SW
13408	4578	4376	4511	Edgewood Valley - 13 SW	\N	t	2025-06-24 19:48:53.499999-05	2025-06-24 19:48:53.499999-05	Series 13 SW
13409	4578	4382	4511	Edgewood Valley - 17 SW	\N	t	2025-06-24 19:48:53.499999-05	2025-06-24 19:48:53.499999-05	Series 17 SW
13410	4578	4386	4511	Edgewood Valley - 23 SW	\N	t	2025-06-24 19:48:53.499999-05	2025-06-24 19:48:53.499999-05	Series 23 SW
13411	4578	4388	4511	Edgewood Valley - 27 SW	\N	t	2025-06-24 19:48:53.499999-05	2025-06-24 19:48:53.499999-05	Series 27 SW
13412	4578	4389	4511	Edgewood Valley - 29 SW	\N	t	2025-06-24 19:48:53.499999-05	2025-06-24 19:48:53.499999-05	Series 29 SW
13413	4578	4410	4511	Edgewood Valley - 7 SW	\N	t	2025-06-24 19:48:53.499999-05	2025-06-24 19:48:53.499999-05	Series 7 SW
13414	4579	4265	4511	Evanston - 13	\N	t	2025-06-24 19:48:53.499999-05	2025-06-24 19:48:53.499999-05	Series 13
13415	4579	4334	4511	Evanston - 13 (Division 13)	\N	t	2025-06-24 19:48:53.499999-05	2025-06-24 19:48:53.499999-05	Series 13 (Division 13)
13416	4579	4271	4511	Evanston - 17	\N	t	2025-06-24 19:48:53.499999-05	2025-06-24 19:48:53.499999-05	Series 17
13417	4579	4342	4511	Evanston - 17 (Division 17)	\N	t	2025-06-24 19:48:53.499999-05	2025-06-24 19:48:53.499999-05	Series 17 (Division 17)
13418	4579	4274	4511	Evanston - 19	\N	t	2025-06-24 19:48:53.499999-05	2025-06-24 19:48:53.499999-05	Series 19
13419	4579	4343	4511	Evanston - 19 (Division 19)	\N	t	2025-06-24 19:48:53.499999-05	2025-06-24 19:48:53.499999-05	Series 19 (Division 19)
13420	4579	4281	4511	Evanston - 23	\N	t	2025-06-24 19:48:53.499999-05	2025-06-24 19:48:53.499999-05	Series 23
13421	4579	4283	4511	Evanston - 24	\N	t	2025-06-24 19:48:53.499999-05	2025-06-24 19:48:53.499999-05	Series 24
13422	4579	4290	4511	Evanston - 29	\N	t	2025-06-24 19:48:53.499999-05	2025-06-24 19:48:53.499999-05	Series 29
13423	4579	4292	4511	Evanston - 3	\N	t	2025-06-24 19:48:53.499999-05	2025-06-24 19:48:53.499999-05	Series 3
13424	4579	4296	4511	Evanston - 30	\N	t	2025-06-24 19:48:53.499999-05	2025-06-24 19:48:53.499999-05	Series 30
13425	4579	4298	4511	Evanston - 32	\N	t	2025-06-24 19:48:53.499999-05	2025-06-24 19:48:53.499999-05	Series 32
13426	4579	4300	4511	Evanston - 34	\N	t	2025-06-24 19:48:53.499999-05	2025-06-24 19:48:53.499999-05	Series 34
13427	4579	4302	4511	Evanston - 36	\N	t	2025-06-24 19:48:53.499999-05	2025-06-24 19:48:53.499999-05	Series 36
13428	4579	4304	4511	Evanston - 38	\N	t	2025-06-24 19:48:53.499999-05	2025-06-24 19:48:53.499999-05	Series 38
13429	4579	4317	4511	Evanston - 7	\N	t	2025-06-24 19:48:53.499999-05	2025-06-24 19:48:53.499999-05	Series 7
13430	4579	4359	4511	Evanston - 7 (Division 7)	\N	t	2025-06-24 19:48:53.499999-05	2025-06-24 19:48:53.499999-05	Series 7 (Division 7)
13431	4579	4320	4511	Evanston - 9	\N	t	2025-06-24 19:48:53.499999-05	2025-06-24 19:48:53.499999-05	Series 9
13432	4579	4363	4511	Evanston - 9 (Division 9)	\N	t	2025-06-24 19:48:53.499999-05	2025-06-24 19:48:53.499999-05	Series 9 (Division 9)
13433	4579	4372	4513	Evanston 11	\N	t	2025-06-24 19:48:53.499999-05	2025-06-24 19:48:53.499999-05	S11
13434	4579	4374	4513	Evanston 12	\N	t	2025-06-24 19:48:53.499999-05	2025-06-24 19:48:53.499999-05	S12
13435	4579	4377	4513	Evanston 14	\N	t	2025-06-24 19:48:53.499999-05	2025-06-24 19:48:53.499999-05	S14
13436	4579	4378	4513	Evanston 15	\N	t	2025-06-24 19:48:53.499999-05	2025-06-24 19:48:53.499999-05	S15
13437	4579	4381	4513	Evanston 17	\N	t	2025-06-24 19:48:53.499999-05	2025-06-24 19:48:53.499999-05	S17
13438	4579	4384	4513	Evanston 2	\N	t	2025-06-24 19:48:53.499999-05	2025-06-24 19:48:53.499999-05	S2
13439	4579	4408	4513	Evanston 6	\N	t	2025-06-24 19:48:53.499999-05	2025-06-24 19:48:53.499999-05	S6
13440	4579	4409	4513	Evanston 7	\N	t	2025-06-24 19:48:53.499999-05	2025-06-24 19:48:53.499999-05	S7
13441	4579	4412	4513	Evanston 9	\N	t	2025-06-24 19:48:53.499999-05	2025-06-24 19:48:53.499999-05	S9
13442	4580	4264	4511	Exmoor - 12	\N	t	2025-06-24 19:48:53.499999-05	2025-06-24 19:48:53.499999-05	Series 12
13443	4580	4268	4511	Exmoor - 15	\N	t	2025-06-24 19:48:53.499999-05	2025-06-24 19:48:53.499999-05	Series 15
13444	4580	4338	4511	Exmoor - 15 (Division 15)	\N	t	2025-06-24 19:48:53.499999-05	2025-06-24 19:48:53.499999-05	Series 15 (Division 15)
13445	4580	4277	4511	Exmoor - 20	\N	t	2025-06-24 19:48:53.499999-05	2025-06-24 19:48:53.499999-05	Series 20
13446	4580	4280	4511	Exmoor - 22	\N	t	2025-06-24 19:48:53.499999-05	2025-06-24 19:48:53.499999-05	Series 22
13447	4580	4286	4511	Exmoor - 26	\N	t	2025-06-24 19:48:53.499999-05	2025-06-24 19:48:53.499999-05	Series 26
13448	4580	4300	4511	Exmoor - 34	\N	t	2025-06-24 19:48:53.499999-05	2025-06-24 19:48:53.499999-05	Series 34
13449	4580	4305	4511	Exmoor - 39	\N	t	2025-06-24 19:48:53.499999-05	2025-06-24 19:48:53.499999-05	Series 39
13450	4580	4319	4511	Exmoor - 8	\N	t	2025-06-24 19:48:53.499999-05	2025-06-24 19:48:53.499999-05	Series 8
13451	4580	4371	4513	Exmoor 10	\N	t	2025-06-24 19:48:53.499999-05	2025-06-24 19:48:53.499999-05	S10
13452	4580	4377	4513	Exmoor 14	\N	t	2025-06-24 19:48:53.499999-05	2025-06-24 19:48:53.499999-05	S14
13453	4580	4380	4513	Exmoor 16	\N	t	2025-06-24 19:48:53.499999-05	2025-06-24 19:48:53.499999-05	S16
13454	4580	4390	4514	Exmoor S2A	\N	t	2025-06-24 19:48:53.499999-05	2025-06-24 19:48:53.499999-05	Series 2A
13455	4580	4397	4513	Exmoor 4	\N	t	2025-06-24 19:48:53.499999-05	2025-06-24 19:48:53.499999-05	S4
13456	4580	4409	4513	Exmoor 7	\N	t	2025-06-24 19:48:53.499999-05	2025-06-24 19:48:53.499999-05	S7
13457	4581	4260	4511	Glen Ellyn - 1	\N	t	2025-06-24 19:48:53.499999-05	2025-06-24 19:48:53.499999-05	Series 1
13458	4581	4292	4511	Glen Ellyn - 3	\N	t	2025-06-24 19:48:53.499999-05	2025-06-24 19:48:53.499999-05	Series 3
13459	4581	4315	4511	Glen Ellyn - 5	\N	t	2025-06-24 19:48:53.499999-05	2025-06-24 19:48:53.499999-05	Series 5
13460	4581	4373	4511	Glen Ellyn - 11 SW	\N	t	2025-06-24 19:48:53.499999-05	2025-06-24 19:48:53.499999-05	Series 11 SW
13461	4581	4376	4511	Glen Ellyn - 13 SW	\N	t	2025-06-24 19:48:53.499999-05	2025-06-24 19:48:53.499999-05	Series 13 SW
13462	4581	4379	4511	Glen Ellyn - 15 SW	\N	t	2025-06-24 19:48:53.499999-05	2025-06-24 19:48:53.499999-05	Series 15 SW
13463	4581	4382	4511	Glen Ellyn - 17 SW	\N	t	2025-06-24 19:48:53.499999-05	2025-06-24 19:48:53.499999-05	Series 17 SW
13464	4581	4383	4511	Glen Ellyn - 19 SW	\N	t	2025-06-24 19:48:53.499999-05	2025-06-24 19:48:53.499999-05	Series 19 SW
13465	4581	4385	4511	Glen Ellyn - 21 SW	\N	t	2025-06-24 19:48:53.499999-05	2025-06-24 19:48:53.499999-05	Series 21 SW
13466	4581	4386	4511	Glen Ellyn - 23 SW	\N	t	2025-06-24 19:48:53.499999-05	2025-06-24 19:48:53.499999-05	Series 23 SW
13467	4581	4388	4511	Glen Ellyn - 27 SW	\N	t	2025-06-24 19:48:53.499999-05	2025-06-24 19:48:53.499999-05	Series 27 SW
13468	4581	4389	4511	Glen Ellyn - 29 SW	\N	t	2025-06-24 19:48:53.499999-05	2025-06-24 19:48:53.499999-05	Series 29 SW
13469	4581	4397	4513	Glen Ellyn 4	\N	t	2025-06-24 19:48:53.499999-05	2025-06-24 19:48:53.499999-05	S4
13470	4581	4410	4511	Glen Ellyn - 7 SW	\N	t	2025-06-24 19:48:53.499999-05	2025-06-24 19:48:53.499999-05	Series 7 SW
13471	4581	4413	4511	Glen Ellyn - 9 SW	\N	t	2025-06-24 19:48:53.499999-05	2025-06-24 19:48:53.499999-05	Series 9 SW
13472	4582	4373	4511	Glen Oak - 11 SW	\N	t	2025-06-24 19:48:53.499999-05	2025-06-24 19:48:53.499999-05	Series 11 SW
13473	4582	4379	4511	Glen Oak - 15 SW	\N	t	2025-06-24 19:48:53.499999-05	2025-06-24 19:48:53.499999-05	Series 15 SW
13474	4582	4383	4511	Glen Oak - 19 SW	\N	t	2025-06-24 19:48:53.499999-05	2025-06-24 19:48:53.499999-05	Series 19 SW
13475	4582	4386	4511	Glen Oak - 23 SW	\N	t	2025-06-24 19:48:53.499999-05	2025-06-24 19:48:53.499999-05	Series 23 SW
13476	4582	4387	4511	Glen Oak - 25 SW	\N	t	2025-06-24 19:48:53.499999-05	2025-06-24 19:48:53.499999-05	Series 25 SW
13477	4583	4388	4511	Glen Oak I - 27 SW	\N	t	2025-06-24 19:48:53.499999-05	2025-06-24 19:48:53.499999-05	Series 27 SW
13478	4584	4388	4511	Glen Oak II - 27 SW	\N	t	2025-06-24 19:48:53.499999-05	2025-06-24 19:48:53.499999-05	Series 27 SW
13479	4585	4260	4511	Glen View - 1	\N	t	2025-06-24 19:48:53.499999-05	2025-06-24 19:48:53.499999-05	Series 1
13480	4585	4268	4511	Glen View - 15	\N	t	2025-06-24 19:48:53.499999-05	2025-06-24 19:48:53.499999-05	Series 15
13481	4585	4338	4511	Glen View - 15 (Division 15)	\N	t	2025-06-24 19:48:53.499999-05	2025-06-24 19:48:53.499999-05	Series 15 (Division 15)
13482	4585	4283	4511	Glen View - 24	\N	t	2025-06-24 19:48:53.499999-05	2025-06-24 19:48:53.499999-05	Series 24
13483	4585	4286	4511	Glen View - 26	\N	t	2025-06-24 19:48:53.499999-05	2025-06-24 19:48:53.499999-05	Series 26
13484	4585	4292	4511	Glen View - 3	\N	t	2025-06-24 19:48:53.499999-05	2025-06-24 19:48:53.499999-05	Series 3
13485	4585	4298	4511	Glen View - 32	\N	t	2025-06-24 19:48:53.499999-05	2025-06-24 19:48:53.499999-05	Series 32
13486	4585	4317	4511	Glen View - 7	\N	t	2025-06-24 19:48:53.499999-05	2025-06-24 19:48:53.499999-05	Series 7
13487	4585	4359	4511	Glen View - 7 (Division 7)	\N	t	2025-06-24 19:48:53.499999-05	2025-06-24 19:48:53.499999-05	Series 7 (Division 7)
13488	4585	4380	4513	Glen View 16	\N	t	2025-06-24 19:48:53.499999-05	2025-06-24 19:48:53.499999-05	S16
13489	4585	4392	4513	Glen View 3	\N	t	2025-06-24 19:48:53.499999-05	2025-06-24 19:48:53.499999-05	S3
13490	4585	4412	4513	Glen View 9	\N	t	2025-06-24 19:48:53.499999-05	2025-06-24 19:48:53.499999-05	S9
13491	4586	4260	4511	Glenbrook RC - 1	\N	t	2025-06-24 19:48:53.499999-05	2025-06-24 19:48:53.499999-05	Series 1
13492	4586	4268	4511	Glenbrook RC - 15	\N	t	2025-06-24 19:48:53.499999-05	2025-06-24 19:48:53.499999-05	Series 15
13493	4586	4338	4511	Glenbrook RC - 15 (Division 15)	\N	t	2025-06-24 19:48:53.499999-05	2025-06-24 19:48:53.499999-05	Series 15 (Division 15)
13494	4586	4270	4511	Glenbrook RC - 16	\N	t	2025-06-24 19:48:53.499999-05	2025-06-24 19:48:53.499999-05	Series 16
13495	4586	4271	4511	Glenbrook RC - 17	\N	t	2025-06-24 19:48:53.499999-05	2025-06-24 19:48:53.499999-05	Series 17
13496	4586	4342	4511	Glenbrook RC - 17 (Division 17)	\N	t	2025-06-24 19:48:53.499999-05	2025-06-24 19:48:53.499999-05	Series 17 (Division 17)
13497	4586	4273	4511	Glenbrook RC - 18	\N	t	2025-06-24 19:48:53.499999-05	2025-06-24 19:48:53.499999-05	Series 18
13498	4586	4277	4511	Glenbrook RC - 20	\N	t	2025-06-24 19:48:53.499999-05	2025-06-24 19:48:53.499999-05	Series 20
13499	4586	4286	4511	Glenbrook RC - 26	\N	t	2025-06-24 19:48:53.499999-05	2025-06-24 19:48:53.499999-05	Series 26
13500	4586	4306	4511	Glenbrook RC - 4	\N	t	2025-06-24 19:48:53.499999-05	2025-06-24 19:48:53.499999-05	Series 4
13501	4586	4319	4511	Glenbrook RC - 8	\N	t	2025-06-24 19:48:53.499999-05	2025-06-24 19:48:53.499999-05	Series 8
13502	4586	4320	4511	Glenbrook RC - 9	\N	t	2025-06-24 19:48:53.499999-05	2025-06-24 19:48:53.499999-05	Series 9
13503	4586	4363	4511	Glenbrook RC - 9 (Division 9)	\N	t	2025-06-24 19:48:53.499999-05	2025-06-24 19:48:53.499999-05	Series 9 (Division 9)
13504	4587	4271	4511	Hawthorn Woods - 17	\N	t	2025-06-24 19:48:53.499999-05	2025-06-24 19:48:53.499999-05	Series 17
13505	4587	4342	4511	Hawthorn Woods - 17 (Division 17)	\N	t	2025-06-24 19:48:53.499999-05	2025-06-24 19:48:53.499999-05	Series 17 (Division 17)
13506	4587	4286	4511	Hawthorn Woods - 26	\N	t	2025-06-24 19:48:53.499999-05	2025-06-24 19:48:53.499999-05	Series 26
13507	4587	4292	4511	Hawthorn Woods - 3	\N	t	2025-06-24 19:48:53.499999-05	2025-06-24 19:48:53.499999-05	Series 3
13508	4587	4300	4511	Hawthorn Woods - 34	\N	t	2025-06-24 19:48:53.499999-05	2025-06-24 19:48:53.499999-05	Series 34
13509	4587	4320	4511	Hawthorn Woods - 9	\N	t	2025-06-24 19:48:53.499999-05	2025-06-24 19:48:53.499999-05	Series 9
13510	4587	4363	4511	Hawthorn Woods - 9 (Division 9)	\N	t	2025-06-24 19:48:53.499999-05	2025-06-24 19:48:53.499999-05	Series 9 (Division 9)
13511	4588	4292	4511	Hinsdale GC - 3	\N	t	2025-06-24 19:48:53.499999-05	2025-06-24 19:48:53.499999-05	Series 3
13512	4588	4373	4511	Hinsdale GC - 11 SW	\N	t	2025-06-24 19:48:53.499999-05	2025-06-24 19:48:53.499999-05	Series 11 SW
13513	4588	4376	4511	Hinsdale GC - 13 SW	\N	t	2025-06-24 19:48:53.499999-05	2025-06-24 19:48:53.499999-05	Series 13 SW
13514	4588	4379	4511	Hinsdale GC - 15 SW	\N	t	2025-06-24 19:48:53.499999-05	2025-06-24 19:48:53.499999-05	Series 15 SW
13515	4588	4382	4511	Hinsdale GC - 17 SW	\N	t	2025-06-24 19:48:53.499999-05	2025-06-24 19:48:53.499999-05	Series 17 SW
13516	4588	4383	4511	Hinsdale GC - 19 SW	\N	t	2025-06-24 19:48:53.499999-05	2025-06-24 19:48:53.499999-05	Series 19 SW
13517	4588	4386	4511	Hinsdale GC - 23 SW	\N	t	2025-06-24 19:48:53.499999-05	2025-06-24 19:48:53.499999-05	Series 23 SW
13518	4588	4387	4511	Hinsdale GC - 25 SW	\N	t	2025-06-24 19:48:53.499999-05	2025-06-24 19:48:53.499999-05	Series 25 SW
13519	4588	4388	4511	Hinsdale GC - 27 SW	\N	t	2025-06-24 19:48:53.499999-05	2025-06-24 19:48:53.499999-05	Series 27 SW
13520	4588	4389	4511	Hinsdale GC - 29 SW	\N	t	2025-06-24 19:48:53.499999-05	2025-06-24 19:48:53.499999-05	Series 29 SW
13521	4589	4407	4513	Hinsdale Golf Club 5	\N	t	2025-06-24 19:48:53.499999-05	2025-06-24 19:48:53.499999-05	S5
13522	4590	4276	4511	Hinsdale PC - 2	\N	t	2025-06-24 19:48:53.499999-05	2025-06-24 19:48:53.499999-05	Series 2
13523	4590	4306	4511	Hinsdale PC - 4	\N	t	2025-06-24 19:48:53.499999-05	2025-06-24 19:48:53.499999-05	Series 4
13524	4590	4315	4511	Hinsdale PC - 5	\N	t	2025-06-24 19:48:53.499999-05	2025-06-24 19:48:53.499999-05	Series 5
13525	4590	4370	4513	Hinsdale PC 1a	\N	t	2025-06-24 19:48:53.499999-05	2025-06-24 19:48:53.499999-05	S1
13526	4590	4373	4511	Hinsdale PC - 11 SW	\N	t	2025-06-24 19:48:53.499999-05	2025-06-24 19:48:53.499999-05	Series 11 SW
13527	4590	4383	4511	Hinsdale PC - 19 SW	\N	t	2025-06-24 19:48:53.499999-05	2025-06-24 19:48:53.499999-05	Series 19 SW
13528	4590	4386	4511	Hinsdale PC - 23 SW	\N	t	2025-06-24 19:48:53.499999-05	2025-06-24 19:48:53.499999-05	Series 23 SW
13529	4590	4389	4511	Hinsdale PC - 29 SW	\N	t	2025-06-24 19:48:53.499999-05	2025-06-24 19:48:53.499999-05	Series 29 SW
13530	4590	4392	4513	Hinsdale PC 3	\N	t	2025-06-24 19:48:53.499999-05	2025-06-24 19:48:53.499999-05	S3
13531	4590	4410	4511	Hinsdale PC - 7 SW	\N	t	2025-06-24 19:48:53.499999-05	2025-06-24 19:48:53.499999-05	Series 7 SW
13532	4591	4376	4511	Hinsdale PC I - 13 SW	\N	t	2025-06-24 19:48:53.499999-05	2025-06-24 19:48:53.499999-05	Series 13 SW
13533	4591	4379	4511	Hinsdale PC I - 15 SW	\N	t	2025-06-24 19:48:53.499999-05	2025-06-24 19:48:53.499999-05	Series 15 SW
13534	4591	4382	4511	Hinsdale PC I - 17 SW	\N	t	2025-06-24 19:48:53.499999-05	2025-06-24 19:48:53.499999-05	Series 17 SW
13535	4591	4385	4511	Hinsdale PC I - 21 SW	\N	t	2025-06-24 19:48:53.499999-05	2025-06-24 19:48:53.499999-05	Series 21 SW
13536	4591	4387	4511	Hinsdale PC I - 25 SW	\N	t	2025-06-24 19:48:53.499999-05	2025-06-24 19:48:53.499999-05	Series 25 SW
13537	4591	4388	4511	Hinsdale PC I - 27 SW	\N	t	2025-06-24 19:48:53.499999-05	2025-06-24 19:48:53.499999-05	Series 27 SW
13538	4591	4413	4511	Hinsdale PC I - 9 SW	\N	t	2025-06-24 19:48:53.499999-05	2025-06-24 19:48:53.499999-05	Series 9 SW
13539	4592	4376	4511	Hinsdale PC II - 13 SW	\N	t	2025-06-24 19:48:53.499999-05	2025-06-24 19:48:53.499999-05	Series 13 SW
13540	4592	4379	4511	Hinsdale PC II - 15 SW	\N	t	2025-06-24 19:48:53.499999-05	2025-06-24 19:48:53.499999-05	Series 15 SW
13541	4592	4382	4511	Hinsdale PC II - 17 SW	\N	t	2025-06-24 19:48:53.499999-05	2025-06-24 19:48:53.499999-05	Series 17 SW
13542	4592	4385	4511	Hinsdale PC II - 21 SW	\N	t	2025-06-24 19:48:53.499999-05	2025-06-24 19:48:53.499999-05	Series 21 SW
13543	4592	4387	4511	Hinsdale PC II - 25 SW	\N	t	2025-06-24 19:48:53.499999-05	2025-06-24 19:48:53.499999-05	Series 25 SW
13544	4592	4388	4511	Hinsdale PC II - 27 SW	\N	t	2025-06-24 19:48:53.499999-05	2025-06-24 19:48:53.499999-05	Series 27 SW
13545	4592	4413	4511	Hinsdale PC II - 9 SW	\N	t	2025-06-24 19:48:53.499999-05	2025-06-24 19:48:53.499999-05	Series 9 SW
13546	4593	4265	4511	Indian Hill - 13	\N	t	2025-06-24 19:48:53.499999-05	2025-06-24 19:48:53.499999-05	Series 13
13547	4593	4334	4511	Indian Hill - 13 (Division 13)	\N	t	2025-06-24 19:48:53.499999-05	2025-06-24 19:48:53.499999-05	Series 13 (Division 13)
13548	4593	4273	4511	Indian Hill - 18	\N	t	2025-06-24 19:48:53.499999-05	2025-06-24 19:48:53.499999-05	Series 18
13549	4593	4281	4511	Indian Hill - 23	\N	t	2025-06-24 19:48:53.499999-05	2025-06-24 19:48:53.499999-05	Series 23
13550	4593	4284	4511	Indian Hill - 25	\N	t	2025-06-24 19:48:53.499999-05	2025-06-24 19:48:53.499999-05	Series 25
13551	4593	4289	4511	Indian Hill - 28	\N	t	2025-06-24 19:48:53.499999-05	2025-06-24 19:48:53.499999-05	Series 28
13552	4593	4292	4511	Indian Hill - 3	\N	t	2025-06-24 19:48:53.499999-05	2025-06-24 19:48:53.499999-05	Series 3
13553	4593	4296	4511	Indian Hill - 30	\N	t	2025-06-24 19:48:53.499999-05	2025-06-24 19:48:53.499999-05	Series 30
13554	4593	4301	4511	Indian Hill - 35	\N	t	2025-06-24 19:48:53.499999-05	2025-06-24 19:48:53.499999-05	Series 35
13555	4593	4319	4511	Indian Hill - 8	\N	t	2025-06-24 19:48:53.499999-05	2025-06-24 19:48:53.499999-05	Series 8
13556	4593	4384	4513	Indian Hill 2	\N	t	2025-06-24 19:48:53.499999-05	2025-06-24 19:48:53.499999-05	S2
13557	4593	4408	4513	Indian Hill 6	\N	t	2025-06-24 19:48:53.499999-05	2025-06-24 19:48:53.499999-05	S6
13558	4594	4268	4511	Inverness - 15	\N	t	2025-06-24 19:48:53.499999-05	2025-06-24 19:48:53.499999-05	Series 15
13559	4594	4338	4511	Inverness - 15 (Division 15)	\N	t	2025-06-24 19:48:53.499999-05	2025-06-24 19:48:53.499999-05	Series 15 (Division 15)
13560	4594	4281	4511	Inverness - 23	\N	t	2025-06-24 19:48:53.499999-05	2025-06-24 19:48:53.499999-05	Series 23
13561	4594	4287	4511	Inverness - 27	\N	t	2025-06-24 19:48:53.499999-05	2025-06-24 19:48:53.499999-05	Series 27
13562	4594	4298	4511	Inverness - 32	\N	t	2025-06-24 19:48:53.499999-05	2025-06-24 19:48:53.499999-05	Series 32
13563	4594	4303	4511	Inverness - 37	\N	t	2025-06-24 19:48:53.499999-05	2025-06-24 19:48:53.499999-05	Series 37
13564	4595	4264	4511	Knollwood - 12	\N	t	2025-06-24 19:48:53.499999-05	2025-06-24 19:48:53.499999-05	Series 12
13565	4595	4271	4511	Knollwood - 17	\N	t	2025-06-24 19:48:53.499999-05	2025-06-24 19:48:53.499999-05	Series 17
13566	4595	4342	4511	Knollwood - 17 (Division 17)	\N	t	2025-06-24 19:48:53.499999-05	2025-06-24 19:48:53.499999-05	Series 17 (Division 17)
13567	4595	4274	4511	Knollwood - 19	\N	t	2025-06-24 19:48:53.499999-05	2025-06-24 19:48:53.499999-05	Series 19
13568	4595	4343	4511	Knollwood - 19 (Division 19)	\N	t	2025-06-24 19:48:53.499999-05	2025-06-24 19:48:53.499999-05	Series 19 (Division 19)
13569	4595	4276	4511	Knollwood - 2	\N	t	2025-06-24 19:48:53.499999-05	2025-06-24 19:48:53.499999-05	Series 2
13570	4595	4278	4511	Knollwood - 21	\N	t	2025-06-24 19:48:53.499999-05	2025-06-24 19:48:53.499999-05	Series 21
13571	4595	4284	4511	Knollwood - 25	\N	t	2025-06-24 19:48:53.499999-05	2025-06-24 19:48:53.499999-05	Series 25
13572	4595	4297	4511	Knollwood - 31	\N	t	2025-06-24 19:48:53.499999-05	2025-06-24 19:48:53.499999-05	Series 31
13573	4595	4299	4511	Knollwood - 33	\N	t	2025-06-24 19:48:53.499999-05	2025-06-24 19:48:53.499999-05	Series 33
13574	4595	4319	4511	Knollwood - 8	\N	t	2025-06-24 19:48:53.499999-05	2025-06-24 19:48:53.499999-05	Series 8
13575	4595	4371	4513	Knollwood 10	\N	t	2025-06-24 19:48:53.499999-05	2025-06-24 19:48:53.499999-05	S10
13576	4595	4374	4513	Knollwood 12	\N	t	2025-06-24 19:48:53.499999-05	2025-06-24 19:48:53.499999-05	S12
13577	4595	4378	4513	Knollwood 15	\N	t	2025-06-24 19:48:53.499999-05	2025-06-24 19:48:53.499999-05	S15
13578	4595	4407	4513	Knollwood 5	\N	t	2025-06-24 19:48:53.499999-05	2025-06-24 19:48:53.499999-05	S5
13579	4595	4411	4513	Knollwood 8	\N	t	2025-06-24 19:48:53.499999-05	2025-06-24 19:48:53.499999-05	S8
13580	4596	4373	4511	LaGrange CC - 11 SW	\N	t	2025-06-24 19:48:53.499999-05	2025-06-24 19:48:53.499999-05	Series 11 SW
13581	4596	4382	4511	LaGrange CC - 17 SW	\N	t	2025-06-24 19:48:53.499999-05	2025-06-24 19:48:53.499999-05	Series 17 SW
13582	4596	4383	4511	LaGrange CC - 19 SW	\N	t	2025-06-24 19:48:53.499999-05	2025-06-24 19:48:53.499999-05	Series 19 SW
13583	4596	4385	4511	LaGrange CC - 21 SW	\N	t	2025-06-24 19:48:53.499999-05	2025-06-24 19:48:53.499999-05	Series 21 SW
13584	4596	4386	4511	LaGrange CC - 23 SW	\N	t	2025-06-24 19:48:53.499999-05	2025-06-24 19:48:53.499999-05	Series 23 SW
13585	4596	4389	4511	LaGrange CC - 29 SW	\N	t	2025-06-24 19:48:53.499999-05	2025-06-24 19:48:53.499999-05	Series 29 SW
13586	4596	4410	4511	LaGrange CC - 7 SW	\N	t	2025-06-24 19:48:53.499999-05	2025-06-24 19:48:53.499999-05	Series 7 SW
13587	4597	4376	4511	LaGrange CC I - 13 SW	\N	t	2025-06-24 19:48:53.499999-05	2025-06-24 19:48:53.499999-05	Series 13 SW
13588	4597	4388	4511	LaGrange CC I - 27 SW	\N	t	2025-06-24 19:48:53.499999-05	2025-06-24 19:48:53.499999-05	Series 27 SW
13589	4598	4376	4511	LaGrange CC II - 13 SW	\N	t	2025-06-24 19:48:53.499999-05	2025-06-24 19:48:53.499999-05	Series 13 SW
13590	4598	4388	4511	LaGrange CC II - 27 SW	\N	t	2025-06-24 19:48:53.499999-05	2025-06-24 19:48:53.499999-05	Series 27 SW
13591	4599	4262	4511	Lake Bluff - 11	\N	t	2025-06-24 19:48:53.499999-05	2025-06-24 19:48:53.499999-05	Series 11
13592	4599	4332	4511	Lake Bluff - 11 (Division 11)	\N	t	2025-06-24 19:48:53.499999-05	2025-06-24 19:48:53.499999-05	Series 11 (Division 11)
13593	4599	4264	4511	Lake Bluff - 12	\N	t	2025-06-24 19:48:53.499999-05	2025-06-24 19:48:53.499999-05	Series 12
13594	4599	4265	4511	Lake Bluff - 13	\N	t	2025-06-24 19:48:53.499999-05	2025-06-24 19:48:53.499999-05	Series 13
13595	4599	4334	4511	Lake Bluff - 13 (Division 13)	\N	t	2025-06-24 19:48:53.499999-05	2025-06-24 19:48:53.499999-05	Series 13 (Division 13)
13596	4599	4277	4511	Lake Bluff - 20	\N	t	2025-06-24 19:48:53.499999-05	2025-06-24 19:48:53.499999-05	Series 20
13597	4599	4278	4511	Lake Bluff - 21	\N	t	2025-06-24 19:48:53.499999-05	2025-06-24 19:48:53.499999-05	Series 21
13598	4599	4280	4511	Lake Bluff - 22	\N	t	2025-06-24 19:48:53.499999-05	2025-06-24 19:48:53.499999-05	Series 22
13599	4599	4287	4511	Lake Bluff - 27	\N	t	2025-06-24 19:48:53.499999-05	2025-06-24 19:48:53.499999-05	Series 27
13600	4599	4297	4511	Lake Bluff - 31	\N	t	2025-06-24 19:48:53.499999-05	2025-06-24 19:48:53.499999-05	Series 31
13601	4599	4301	4511	Lake Bluff - 35	\N	t	2025-06-24 19:48:53.499999-05	2025-06-24 19:48:53.499999-05	Series 35
13602	4599	4303	4511	Lake Bluff - 37	\N	t	2025-06-24 19:48:53.499999-05	2025-06-24 19:48:53.499999-05	Series 37
13603	4599	4304	4511	Lake Bluff - 38	\N	t	2025-06-24 19:48:53.499999-05	2025-06-24 19:48:53.499999-05	Series 38
13604	4599	4306	4511	Lake Bluff - 4	\N	t	2025-06-24 19:48:53.499999-05	2025-06-24 19:48:53.499999-05	Series 4
13605	4599	4315	4511	Lake Bluff - 5	\N	t	2025-06-24 19:48:53.499999-05	2025-06-24 19:48:53.499999-05	Series 5
13606	4599	4320	4511	Lake Bluff - 9	\N	t	2025-06-24 19:48:53.499999-05	2025-06-24 19:48:53.499999-05	Series 9
13607	4599	4363	4511	Lake Bluff - 9 (Division 9)	\N	t	2025-06-24 19:48:53.499999-05	2025-06-24 19:48:53.499999-05	Series 9 (Division 9)
13608	4599	4370	4513	Lake Bluff 1	\N	t	2025-06-24 19:48:53.499999-05	2025-06-24 19:48:53.499999-05	S1
13609	4599	4371	4513	Lake Bluff 10	\N	t	2025-06-24 19:48:53.499999-05	2025-06-24 19:48:53.499999-05	S10
13610	4599	4375	4513	Lake Bluff 13	\N	t	2025-06-24 19:48:53.499999-05	2025-06-24 19:48:53.499999-05	S13
13611	4599	4380	4513	Lake Bluff 16	\N	t	2025-06-24 19:48:53.499999-05	2025-06-24 19:48:53.499999-05	S16
13612	4599	4397	4513	Lake Bluff 4	\N	t	2025-06-24 19:48:53.499999-05	2025-06-24 19:48:53.499999-05	S4
13613	4599	4409	4513	Lake Bluff 7	\N	t	2025-06-24 19:48:53.499999-05	2025-06-24 19:48:53.499999-05	S7
13614	4600	4264	4511	Lake Forest - 12	\N	t	2025-06-24 19:48:53.499999-05	2025-06-24 19:48:53.499999-05	Series 12
13615	4600	4270	4511	Lake Forest - 16	\N	t	2025-06-24 19:48:53.499999-05	2025-06-24 19:48:53.499999-05	Series 16
13616	4600	4277	4511	Lake Forest - 20	\N	t	2025-06-24 19:48:53.499999-05	2025-06-24 19:48:53.499999-05	Series 20
13617	4600	4280	4511	Lake Forest - 22	\N	t	2025-06-24 19:48:53.499999-05	2025-06-24 19:48:53.499999-05	Series 22
13618	4600	4281	4511	Lake Forest - 23	\N	t	2025-06-24 19:48:53.499999-05	2025-06-24 19:48:53.499999-05	Series 23
13619	4600	4289	4511	Lake Forest - 28	\N	t	2025-06-24 19:48:53.499999-05	2025-06-24 19:48:53.499999-05	Series 28
13620	4600	4292	4511	Lake Forest - 3	\N	t	2025-06-24 19:48:53.499999-05	2025-06-24 19:48:53.499999-05	Series 3
13621	4600	4296	4511	Lake Forest - 30	\N	t	2025-06-24 19:48:53.499999-05	2025-06-24 19:48:53.499999-05	Series 30
13622	4600	4301	4511	Lake Forest - 35	\N	t	2025-06-24 19:48:53.499999-05	2025-06-24 19:48:53.499999-05	Series 35
13623	4600	4305	4511	Lake Forest - 39	\N	t	2025-06-24 19:48:53.499999-05	2025-06-24 19:48:53.499999-05	Series 39
13624	4600	4319	4511	Lake Forest - 8	\N	t	2025-06-24 19:48:53.499999-05	2025-06-24 19:48:53.499999-05	Series 8
13625	4600	4370	4514	Lake Forest  S1	\N	t	2025-06-24 19:48:53.499999-05	2025-06-24 19:48:53.499999-05	Series 1
13626	4600	4374	4513	Lake Forest 12	\N	t	2025-06-24 19:48:53.499999-05	2025-06-24 19:48:53.499999-05	S12
13627	4600	4377	4513	Lake Forest 14	\N	t	2025-06-24 19:48:53.499999-05	2025-06-24 19:48:53.499999-05	S14
13628	4600	4391	4514	Lake Forest S2B	\N	t	2025-06-24 19:48:53.499999-05	2025-06-24 19:48:53.499999-05	Series 2B
13629	4600	4392	4514	Lake Forest S3	\N	t	2025-06-24 19:48:53.499999-05	2025-06-24 19:48:53.499999-05	Series 3
13630	4600	4407	4513	Lake Forest 5	\N	t	2025-06-24 19:48:53.499999-05	2025-06-24 19:48:53.499999-05	S5
13631	4600	4408	4513	Lake Forest 6	\N	t	2025-06-24 19:48:53.499999-05	2025-06-24 19:48:53.499999-05	S6
13632	4601	4271	4511	Lake Shore CC - 17	\N	t	2025-06-24 19:48:53.499999-05	2025-06-24 19:48:53.499999-05	Series 17
13633	4601	4342	4511	Lake Shore CC - 17 (Division 17)	\N	t	2025-06-24 19:48:53.499999-05	2025-06-24 19:48:53.499999-05	Series 17 (Division 17)
13634	4601	4280	4511	Lake Shore CC - 22	\N	t	2025-06-24 19:48:53.499999-05	2025-06-24 19:48:53.499999-05	Series 22
13635	4601	4292	4511	Lake Shore CC - 3	\N	t	2025-06-24 19:48:53.499999-05	2025-06-24 19:48:53.499999-05	Series 3
13636	4601	4299	4511	Lake Shore CC - 33	\N	t	2025-06-24 19:48:53.499999-05	2025-06-24 19:48:53.499999-05	Series 33
13637	4601	4372	4513	Lake Shore CC 11	\N	t	2025-06-24 19:48:53.499999-05	2025-06-24 19:48:53.499999-05	S11
13638	4601	4378	4513	Lake Shore CC 15	\N	t	2025-06-24 19:48:53.499999-05	2025-06-24 19:48:53.499999-05	S15
13639	4601	4384	4513	Lake Shore CC 2	\N	t	2025-06-24 19:48:53.499999-05	2025-06-24 19:48:53.499999-05	S2
13640	4602	4264	4511	Lakeshore S&F - 12	\N	t	2025-06-24 19:48:53.499999-05	2025-06-24 19:48:53.499999-05	Series 12
13641	4602	4267	4511	Lakeshore S&F - 14	\N	t	2025-06-24 19:48:53.499999-05	2025-06-24 19:48:53.499999-05	Series 14
13642	4602	4271	4511	Lakeshore S&F - 17	\N	t	2025-06-24 19:48:53.499999-05	2025-06-24 19:48:53.499999-05	Series 17
13643	4602	4342	4511	Lakeshore S&F - 17 (Division 17)	\N	t	2025-06-24 19:48:53.499999-05	2025-06-24 19:48:53.499999-05	Series 17 (Division 17)
13644	4602	4276	4511	Lakeshore S&F - 2	\N	t	2025-06-24 19:48:53.499999-05	2025-06-24 19:48:53.499999-05	Series 2
13645	4602	4280	4511	Lakeshore S&F - 22	\N	t	2025-06-24 19:48:53.499999-05	2025-06-24 19:48:53.499999-05	Series 22
13646	4602	4292	4511	Lakeshore S&F - 3	\N	t	2025-06-24 19:48:53.499999-05	2025-06-24 19:48:53.499999-05	Series 3
13647	4602	4296	4511	Lakeshore S&F - 30	\N	t	2025-06-24 19:48:53.499999-05	2025-06-24 19:48:53.499999-05	Series 30
13648	4602	4315	4511	Lakeshore S&F - 5	\N	t	2025-06-24 19:48:53.499999-05	2025-06-24 19:48:53.499999-05	Series 5
13649	4602	4317	4511	Lakeshore S&F - 7	\N	t	2025-06-24 19:48:53.499999-05	2025-06-24 19:48:53.499999-05	Series 7
13650	4602	4359	4511	Lakeshore S&F - 7 (Division 7)	\N	t	2025-06-24 19:48:53.499999-05	2025-06-24 19:48:53.499999-05	Series 7 (Division 7)
13651	4603	4370	4513	LifeSport 1	\N	t	2025-06-24 19:48:53.499999-05	2025-06-24 19:48:53.499999-05	S1
13652	4604	4260	4511	Lifesport-Lshire - 1	\N	t	2025-06-24 19:48:53.499999-05	2025-06-24 19:48:53.499999-05	Series 1
13653	4604	4261	4511	Lifesport-Lshire - 10	\N	t	2025-06-24 19:48:53.499999-05	2025-06-24 19:48:53.499999-05	Series 10
13654	4604	4299	4511	Lifesport-Lshire - 33	\N	t	2025-06-24 19:48:53.499999-05	2025-06-24 19:48:53.499999-05	Series 33
13655	4604	4315	4511	Lifesport-Lshire - 5	\N	t	2025-06-24 19:48:53.499999-05	2025-06-24 19:48:53.499999-05	Series 5
13656	4605	4373	4511	Medinah - 11 SW	\N	t	2025-06-24 19:48:53.499999-05	2025-06-24 19:48:53.499999-05	Series 11 SW
13657	4605	4379	4511	Medinah - 15 SW	\N	t	2025-06-24 19:48:53.499999-05	2025-06-24 19:48:53.499999-05	Series 15 SW
13658	4605	4382	4511	Medinah - 17 SW	\N	t	2025-06-24 19:48:53.499999-05	2025-06-24 19:48:53.499999-05	Series 17 SW
13659	4605	4385	4511	Medinah - 21 SW	\N	t	2025-06-24 19:48:53.499999-05	2025-06-24 19:48:53.499999-05	Series 21 SW
13660	4605	4387	4511	Medinah - 25 SW	\N	t	2025-06-24 19:48:53.499999-05	2025-06-24 19:48:53.499999-05	Series 25 SW
13661	4605	4389	4511	Medinah - 29 SW	\N	t	2025-06-24 19:48:53.499999-05	2025-06-24 19:48:53.499999-05	Series 29 SW
13662	4605	4413	4511	Medinah - 9 SW	\N	t	2025-06-24 19:48:53.499999-05	2025-06-24 19:48:53.499999-05	Series 9 SW
13663	4606	4386	4511	Medinah I - 23 SW	\N	t	2025-06-24 19:48:53.499999-05	2025-06-24 19:48:53.499999-05	Series 23 SW
13664	4607	4386	4511	Medinah II - 23 SW	\N	t	2025-06-24 19:48:53.499999-05	2025-06-24 19:48:53.499999-05	Series 23 SW
13665	4608	4264	4511	Michigan Shores - 12	\N	t	2025-06-24 19:48:53.499999-05	2025-06-24 19:48:53.499999-05	Series 12
13666	4608	4267	4511	Michigan Shores - 14	\N	t	2025-06-24 19:48:53.499999-05	2025-06-24 19:48:53.499999-05	Series 14
13667	4608	4270	4511	Michigan Shores - 16	\N	t	2025-06-24 19:48:53.499999-05	2025-06-24 19:48:53.499999-05	Series 16
13668	4608	4273	4511	Michigan Shores - 18	\N	t	2025-06-24 19:48:53.499999-05	2025-06-24 19:48:53.499999-05	Series 18
13669	4608	4276	4511	Michigan Shores - 2	\N	t	2025-06-24 19:48:53.499999-05	2025-06-24 19:48:53.499999-05	Series 2
13670	4608	4280	4511	Michigan Shores - 22	\N	t	2025-06-24 19:48:53.499999-05	2025-06-24 19:48:53.499999-05	Series 22
13671	4608	4286	4511	Michigan Shores - 26	\N	t	2025-06-24 19:48:53.499999-05	2025-06-24 19:48:53.499999-05	Series 26
13672	4608	4296	4511	Michigan Shores - 30	\N	t	2025-06-24 19:48:53.499999-05	2025-06-24 19:48:53.499999-05	Series 30
13673	4608	4300	4511	Michigan Shores - 34	\N	t	2025-06-24 19:48:53.499999-05	2025-06-24 19:48:53.499999-05	Series 34
13674	4608	4301	4511	Michigan Shores - 35	\N	t	2025-06-24 19:48:53.499999-05	2025-06-24 19:48:53.499999-05	Series 35
13675	4608	4303	4511	Michigan Shores - 37	\N	t	2025-06-24 19:48:53.499999-05	2025-06-24 19:48:53.499999-05	Series 37
13676	4608	4316	4511	Michigan Shores - 6	\N	t	2025-06-24 19:48:53.499999-05	2025-06-24 19:48:53.499999-05	Series 6
13677	4608	4358	4511	Michigan Shores - 6 (Division 6)	\N	t	2025-06-24 19:48:53.499999-05	2025-06-24 19:48:53.499999-05	Series 6 (Division 6)
13678	4608	4370	4513	Michigan Shores 1	\N	t	2025-06-24 19:48:53.499999-05	2025-06-24 19:48:53.499999-05	S1
13679	4608	4371	4513	Michigan Shores 10	\N	t	2025-06-24 19:48:53.499999-05	2025-06-24 19:48:53.499999-05	S10
13680	4608	4375	4513	Michigan Shores 13	\N	t	2025-06-24 19:48:53.499999-05	2025-06-24 19:48:53.499999-05	S13
13681	4608	4377	4513	Michigan Shores 14	\N	t	2025-06-24 19:48:53.499999-05	2025-06-24 19:48:53.499999-05	S14
13682	4608	4381	4513	Michigan Shores 17	\N	t	2025-06-24 19:48:53.499999-05	2025-06-24 19:48:53.499999-05	S17
13683	4608	4392	4513	Michigan Shores 3a	\N	t	2025-06-24 19:48:53.499999-05	2025-06-24 19:48:53.499999-05	S3
13684	4608	4408	4513	Michigan Shores 6	\N	t	2025-06-24 19:48:53.499999-05	2025-06-24 19:48:53.499999-05	S6
13685	4608	4409	4513	Michigan Shores 7	\N	t	2025-06-24 19:48:53.499999-05	2025-06-24 19:48:53.499999-05	S7
13686	4608	4411	4513	Michigan Shores 8	\N	t	2025-06-24 19:48:53.499999-05	2025-06-24 19:48:53.499999-05	S8
13687	4608	4412	4513	Michigan Shores 9	\N	t	2025-06-24 19:48:53.499999-05	2025-06-24 19:48:53.499999-05	S9
13688	4609	4273	4511	Midt-Bannockburn - 18	\N	t	2025-06-24 19:48:53.499999-05	2025-06-24 19:48:53.499999-05	Series 18
13689	4609	4284	4511	Midt-Bannockburn - 25	\N	t	2025-06-24 19:48:53.499999-05	2025-06-24 19:48:53.499999-05	Series 25
13690	4609	4290	4511	Midt-Bannockburn - 29	\N	t	2025-06-24 19:48:53.499999-05	2025-06-24 19:48:53.499999-05	Series 29
13691	4609	4304	4511	Midt-Bannockburn - 38	\N	t	2025-06-24 19:48:53.499999-05	2025-06-24 19:48:53.499999-05	Series 38
13692	4610	4257	4512	Midtown - Bannockburn - 3.0 & Under Thur	\N	t	2025-06-24 19:48:53.499999-05	2025-06-24 19:48:53.499999-05	Series Bannockburn
13693	4610	4259	4511	Midtown - Chicago - 19	\N	t	2025-06-24 19:48:53.499999-05	2025-06-24 19:48:53.499999-05	Series Chicago
13694	4610	4274	4511	Midtown - Chicago - 19 (Chicago 19)	\N	t	2025-06-24 19:48:53.499999-05	2025-06-24 19:48:53.499999-05	Series Chicago
13695	4610	4259	4512	Midtown - Chicago - 3.0 & Under Thur	\N	t	2025-06-24 19:48:53.499999-05	2025-06-24 19:48:53.499999-05	Series Chicago
13696	4610	4261	4511	Midtown - Chicago - 10	\N	t	2025-06-24 19:48:53.499999-05	2025-06-24 19:48:53.499999-05	Series Chicago
13697	4610	4267	4511	Midtown - Chicago - 14	\N	t	2025-06-24 19:48:53.499999-05	2025-06-24 19:48:53.499999-05	Series Chicago
13698	4610	4281	4511	Midtown - Chicago - 23	\N	t	2025-06-24 19:48:53.499999-05	2025-06-24 19:48:53.499999-05	Series Chicago
13699	4610	4287	4511	Midtown - Chicago - 27	\N	t	2025-06-24 19:48:53.499999-05	2025-06-24 19:48:53.499999-05	Series Chicago
13700	4610	4298	4511	Midtown - Chicago - 32	\N	t	2025-06-24 19:48:53.499999-05	2025-06-24 19:48:53.499999-05	Series Chicago
13701	4610	4306	4511	Midtown - Chicago - 4	\N	t	2025-06-24 19:48:53.499999-05	2025-06-24 19:48:53.499999-05	Series Chicago
13702	4610	4316	4511	Midtown - Chicago - 6	\N	t	2025-06-24 19:48:53.499999-05	2025-06-24 19:48:53.499999-05	Series Chicago
13703	4610	4323	4512	Midtown - Bannockburn 1 - 4.5 & Under Fri	\N	t	2025-06-24 19:48:53.499999-05	2025-06-24 19:48:53.499999-05	Series Bannockburn 1
13704	4610	4324	4512	Midtown - Bannockburn 2 - 4.5 & Under Fri	\N	t	2025-06-24 19:48:53.499999-05	2025-06-24 19:48:53.499999-05	Series Bannockburn 2
13705	4610	4326	4512	Midtown - Chicago 1 - 3.5 & Under Wed	\N	t	2025-06-24 19:48:53.499999-05	2025-06-24 19:48:53.499999-05	Series Chicago 1
13706	4610	4327	4512	Midtown - Chicago 2 - 3.5 & Under Wed	\N	t	2025-06-24 19:48:53.499999-05	2025-06-24 19:48:53.499999-05	Series Chicago 2
13707	4610	4369	4512	Midtown - Palatine - 3.0 & Under Thur	\N	t	2025-06-24 19:48:53.499999-05	2025-06-24 19:48:53.499999-05	Series Palatine
13708	4610	4370	4513	Midtown 1	\N	t	2025-06-24 19:48:53.499999-05	2025-06-24 19:48:53.499999-05	S1
13709	4610	4370	4514	Midtown S1	\N	t	2025-06-24 19:48:53.499999-05	2025-06-24 19:48:53.499999-05	Series 1
13710	4610	4375	4513	Midtown 13	\N	t	2025-06-24 19:48:53.499999-05	2025-06-24 19:48:53.499999-05	S13
13711	4610	4390	4514	Midtown S2A	\N	t	2025-06-24 19:48:53.499999-05	2025-06-24 19:48:53.499999-05	Series 2A
13712	4610	4393	4512	Midtown - Bannockburn	\N	t	2025-06-24 19:48:53.499999-05	2025-06-24 19:48:53.499999-05	Series Bannockburn
13713	4610	4395	4512	Midtown - Bannockburn (S3.5 & Under Sat)	\N	t	2025-06-24 19:48:53.499999-05	2025-06-24 19:48:53.499999-05	Series Bannockburn (S3.5 & Under Sat)
13714	4610	4399	4512	Midtown - Bannockburn (S4.0 & Under Sat)	\N	t	2025-06-24 19:48:53.499999-05	2025-06-24 19:48:53.499999-05	Series Bannockburn (S4.0 & Under Sat)
13715	4610	4400	4512	Midtown - Bannockburn (S4.0 & Under Wed)	\N	t	2025-06-24 19:48:53.499999-05	2025-06-24 19:48:53.499999-05	Series Bannockburn (S4.0 & Under Wed)
13716	4610	4401	4512	Midtown - Bannockburn (S4.0 - 4.5 Singles Thur)	\N	t	2025-06-24 19:48:53.499999-05	2025-06-24 19:48:53.499999-05	Series Bannockburn (S4.0
13717	4610	4402	4512	Midtown - Bannockburn (S4.0 Singles Sun)	\N	t	2025-06-24 19:48:53.499999-05	2025-06-24 19:48:53.499999-05	Series Bannockburn (S4.0 Singles Sun)
13718	4610	4405	4512	Midtown - Bannockburn (S4.5 Singles Sun)	\N	t	2025-06-24 19:48:53.499999-05	2025-06-24 19:48:53.499999-05	Series Bannockburn (S4.5 Singles Sun)
13719	4610	4416	4512	Midtown - Bannockburn (SBoys)	\N	t	2025-06-24 19:48:53.499999-05	2025-06-24 19:48:53.499999-05	Series Bannockburn (SBoys)
13720	4610	4428	4512	Midtown - Bannockburn (SOpen Fri)	\N	t	2025-06-24 19:48:53.499999-05	2025-06-24 19:48:53.499999-05	Series Bannockburn (SOpen Fri)
13721	4610	4394	4512	Midtown - Palatine	\N	t	2025-06-24 19:48:53.499999-05	2025-06-24 19:48:53.499999-05	Series Palatine
13722	4610	4404	4512	Midtown - Palatine (S4.5 & Under Sat)	\N	t	2025-06-24 19:48:53.499999-05	2025-06-24 19:48:53.499999-05	Series Palatine (S4.5 & Under Sat)
13723	4610	4396	4512	Midtown - Chicago 1	\N	t	2025-06-24 19:48:53.499999-05	2025-06-24 19:48:53.499999-05	Series Chicago 1
13724	4610	4398	4512	Midtown - Chicago 1 (S4.0 & Under Fri)	\N	t	2025-06-24 19:48:53.499999-05	2025-06-24 19:48:53.499999-05	Series Chicago 1 (S4.0 & Under Fri)
13725	4610	4403	4512	Midtown - Bannockburn 1	\N	t	2025-06-24 19:48:53.499999-05	2025-06-24 19:48:53.499999-05	Series Bannockburn 1
13726	4610	4408	4513	Midtown 6	\N	t	2025-06-24 19:48:53.499999-05	2025-06-24 19:48:53.499999-05	S6
13727	4610	4411	4513	Midtown 8	\N	t	2025-06-24 19:48:53.499999-05	2025-06-24 19:48:53.499999-05	S8
13728	4611	4262	4511	North Shore - 11	\N	t	2025-06-24 19:48:53.499999-05	2025-06-24 19:48:53.499999-05	Series 11
13729	4611	4332	4511	North Shore - 11 (Division 11)	\N	t	2025-06-24 19:48:53.499999-05	2025-06-24 19:48:53.499999-05	Series 11 (Division 11)
13730	4611	4268	4511	North Shore - 15	\N	t	2025-06-24 19:48:53.499999-05	2025-06-24 19:48:53.499999-05	Series 15
13731	4611	4338	4511	North Shore - 15 (Division 15)	\N	t	2025-06-24 19:48:53.499999-05	2025-06-24 19:48:53.499999-05	Series 15 (Division 15)
13732	4611	4270	4511	North Shore - 16	\N	t	2025-06-24 19:48:53.499999-05	2025-06-24 19:48:53.499999-05	Series 16
13733	4611	4277	4511	North Shore - 20	\N	t	2025-06-24 19:48:53.499999-05	2025-06-24 19:48:53.499999-05	Series 20
13734	4611	4284	4511	North Shore - 25	\N	t	2025-06-24 19:48:53.499999-05	2025-06-24 19:48:53.499999-05	Series 25
13735	4611	4292	4511	North Shore - 3	\N	t	2025-06-24 19:48:53.499999-05	2025-06-24 19:48:53.499999-05	Series 3
13736	4611	4296	4511	North Shore - 30	\N	t	2025-06-24 19:48:53.499999-05	2025-06-24 19:48:53.499999-05	Series 30
13737	4611	4298	4511	North Shore - 32	\N	t	2025-06-24 19:48:53.499999-05	2025-06-24 19:48:53.499999-05	Series 32
13738	4611	4302	4511	North Shore - 36	\N	t	2025-06-24 19:48:53.499999-05	2025-06-24 19:48:53.499999-05	Series 36
13739	4611	4304	4511	North Shore - 38	\N	t	2025-06-24 19:48:53.499999-05	2025-06-24 19:48:53.499999-05	Series 38
13740	4611	4371	4513	North Shore 10	\N	t	2025-06-24 19:48:53.499999-05	2025-06-24 19:48:53.499999-05	S10
13741	4611	4375	4513	North Shore 13	\N	t	2025-06-24 19:48:53.499999-05	2025-06-24 19:48:53.499999-05	S13
13742	4611	4378	4513	North Shore 15	\N	t	2025-06-24 19:48:53.499999-05	2025-06-24 19:48:53.499999-05	S15
13743	4611	4380	4513	North Shore 16	\N	t	2025-06-24 19:48:53.499999-05	2025-06-24 19:48:53.499999-05	S16
13744	4611	4384	4513	North Shore 2	\N	t	2025-06-24 19:48:53.499999-05	2025-06-24 19:48:53.499999-05	S2
13745	4611	4392	4513	North Shore 3	\N	t	2025-06-24 19:48:53.499999-05	2025-06-24 19:48:53.499999-05	S3
13746	4611	4407	4513	North Shore 5	\N	t	2025-06-24 19:48:53.499999-05	2025-06-24 19:48:53.499999-05	S5
13747	4611	4411	4513	North Shore 8	\N	t	2025-06-24 19:48:53.499999-05	2025-06-24 19:48:53.499999-05	S8
13748	4612	4265	4511	Northmoor - 13	\N	t	2025-06-24 19:48:53.499999-05	2025-06-24 19:48:53.499999-05	Series 13
13749	4612	4334	4511	Northmoor - 13 (Division 13)	\N	t	2025-06-24 19:48:53.499999-05	2025-06-24 19:48:53.499999-05	Series 13 (Division 13)
13750	4612	4278	4511	Northmoor - 21	\N	t	2025-06-24 19:48:53.499999-05	2025-06-24 19:48:53.499999-05	Series 21
13751	4612	4286	4511	Northmoor - 26	\N	t	2025-06-24 19:48:53.499999-05	2025-06-24 19:48:53.499999-05	Series 26
13752	4612	4290	4511	Northmoor - 29	\N	t	2025-06-24 19:48:53.499999-05	2025-06-24 19:48:53.499999-05	Series 29
13753	4612	4292	4511	Northmoor - 3	\N	t	2025-06-24 19:48:53.499999-05	2025-06-24 19:48:53.499999-05	Series 3
13754	4612	4372	4513	Northmoor 11	\N	t	2025-06-24 19:48:53.499999-05	2025-06-24 19:48:53.499999-05	S11
13755	4612	4384	4513	Northmoor 2	\N	t	2025-06-24 19:48:53.499999-05	2025-06-24 19:48:53.499999-05	S2
13756	4612	4390	4514	Northmoor S2A	\N	t	2025-06-24 19:48:53.499999-05	2025-06-24 19:48:53.499999-05	Series 2A
13757	4612	4409	4513	Northmoor 7	\N	t	2025-06-24 19:48:53.499999-05	2025-06-24 19:48:53.499999-05	S7
13758	4613	4376	4511	Oak Park CC - 13 SW	\N	t	2025-06-24 19:48:53.499999-05	2025-06-24 19:48:53.499999-05	Series 13 SW
13759	4613	4385	4511	Oak Park CC - 21 SW	\N	t	2025-06-24 19:48:53.499999-05	2025-06-24 19:48:53.499999-05	Series 21 SW
13760	4613	4388	4511	Oak Park CC - 27 SW	\N	t	2025-06-24 19:48:53.499999-05	2025-06-24 19:48:53.499999-05	Series 27 SW
13761	4613	4413	4511	Oak Park CC - 9 SW	\N	t	2025-06-24 19:48:53.499999-05	2025-06-24 19:48:53.499999-05	Series 9 SW
13762	4614	4389	4511	Oak Park CC I - 29 SW	\N	t	2025-06-24 19:48:53.499999-05	2025-06-24 19:48:53.499999-05	Series 29 SW
13763	4615	4389	4511	Oak Park CC II - 29 SW	\N	t	2025-06-24 19:48:53.499999-05	2025-06-24 19:48:53.499999-05	Series 29 SW
13764	4616	4390	4514	Old Willow S2A	\N	t	2025-06-24 19:48:53.499999-05	2025-06-24 19:48:53.499999-05	Series 2A
13765	4616	4392	4514	Old Willow S3	\N	t	2025-06-24 19:48:53.499999-05	2025-06-24 19:48:53.499999-05	Series 3
13766	4617	4268	4511	Onwentsia - 15	\N	t	2025-06-24 19:48:53.499999-05	2025-06-24 19:48:53.499999-05	Series 15
13767	4617	4338	4511	Onwentsia - 15 (Division 15)	\N	t	2025-06-24 19:48:53.499999-05	2025-06-24 19:48:53.499999-05	Series 15 (Division 15)
13768	4617	4277	4511	Onwentsia - 20	\N	t	2025-06-24 19:48:53.499999-05	2025-06-24 19:48:53.499999-05	Series 20
13769	4617	4315	4511	Onwentsia - 5	\N	t	2025-06-24 19:48:53.499999-05	2025-06-24 19:48:53.499999-05	Series 5
13770	4617	4392	4513	Onwentsia 3	\N	t	2025-06-24 19:48:53.499999-05	2025-06-24 19:48:53.499999-05	S3
13771	4617	4412	4513	Onwentsia 9	\N	t	2025-06-24 19:48:53.499999-05	2025-06-24 19:48:53.499999-05	S9
13772	4618	4371	4513	Park Ridge 10	\N	t	2025-06-24 19:48:53.499999-05	2025-06-24 19:48:53.499999-05	S10
13773	4618	4374	4513	Park Ridge 12	\N	t	2025-06-24 19:48:53.499999-05	2025-06-24 19:48:53.499999-05	S12
13774	4618	4377	4513	Park Ridge 14	\N	t	2025-06-24 19:48:53.499999-05	2025-06-24 19:48:53.499999-05	S14
13775	4618	4381	4513	Park Ridge 17	\N	t	2025-06-24 19:48:53.499999-05	2025-06-24 19:48:53.499999-05	S17
13776	4618	4397	4513	Park Ridge 4	\N	t	2025-06-24 19:48:53.499999-05	2025-06-24 19:48:53.499999-05	S4
13777	4618	4409	4513	Park Ridge 7	\N	t	2025-06-24 19:48:53.499999-05	2025-06-24 19:48:53.499999-05	S7
13778	4618	4412	4513	Park Ridge 9	\N	t	2025-06-24 19:48:53.499999-05	2025-06-24 19:48:53.499999-05	S9
13779	4619	4264	4511	Park Ridge CC - 12	\N	t	2025-06-24 19:48:53.499999-05	2025-06-24 19:48:53.499999-05	Series 12
13780	4619	4281	4511	Park Ridge CC - 23	\N	t	2025-06-24 19:48:53.499999-05	2025-06-24 19:48:53.499999-05	Series 23
13781	4619	4284	4511	Park Ridge CC - 25	\N	t	2025-06-24 19:48:53.499999-05	2025-06-24 19:48:53.499999-05	Series 25
13782	4619	4286	4511	Park Ridge CC - 26	\N	t	2025-06-24 19:48:53.499999-05	2025-06-24 19:48:53.499999-05	Series 26
13783	4619	4287	4511	Park Ridge CC - 27	\N	t	2025-06-24 19:48:53.499999-05	2025-06-24 19:48:53.499999-05	Series 27
13784	4619	4290	4511	Park Ridge CC - 29	\N	t	2025-06-24 19:48:53.499999-05	2025-06-24 19:48:53.499999-05	Series 29
13785	4619	4296	4511	Park Ridge CC - 30	\N	t	2025-06-24 19:48:53.499999-05	2025-06-24 19:48:53.499999-05	Series 30
13786	4619	4297	4511	Park Ridge CC - 31	\N	t	2025-06-24 19:48:53.499999-05	2025-06-24 19:48:53.499999-05	Series 31
13787	4619	4300	4511	Park Ridge CC - 34	\N	t	2025-06-24 19:48:53.499999-05	2025-06-24 19:48:53.499999-05	Series 34
13788	4619	4303	4511	Park Ridge CC - 37	\N	t	2025-06-24 19:48:53.499999-05	2025-06-24 19:48:53.499999-05	Series 37
13789	4619	4319	4511	Park Ridge CC - 8	\N	t	2025-06-24 19:48:53.499999-05	2025-06-24 19:48:53.499999-05	Series 8
13790	4620	4262	4511	Prairie Club - 11	\N	t	2025-06-24 19:48:53.499999-05	2025-06-24 19:48:53.499999-05	Series 11
13791	4620	4332	4511	Prairie Club - 11 (Division 11)	\N	t	2025-06-24 19:48:53.499999-05	2025-06-24 19:48:53.499999-05	Series 11 (Division 11)
13792	4620	4265	4511	Prairie Club - 13	\N	t	2025-06-24 19:48:53.499999-05	2025-06-24 19:48:53.499999-05	Series 13
13793	4620	4334	4511	Prairie Club - 13 (Division 13)	\N	t	2025-06-24 19:48:53.499999-05	2025-06-24 19:48:53.499999-05	Series 13 (Division 13)
13794	4620	4268	4511	Prairie Club - 15	\N	t	2025-06-24 19:48:53.499999-05	2025-06-24 19:48:53.499999-05	Series 15
13795	4620	4338	4511	Prairie Club - 15 (Division 15)	\N	t	2025-06-24 19:48:53.499999-05	2025-06-24 19:48:53.499999-05	Series 15 (Division 15)
13796	4620	4271	4511	Prairie Club - 17	\N	t	2025-06-24 19:48:53.499999-05	2025-06-24 19:48:53.499999-05	Series 17
13797	4620	4342	4511	Prairie Club - 17 (Division 17)	\N	t	2025-06-24 19:48:53.499999-05	2025-06-24 19:48:53.499999-05	Series 17 (Division 17)
13798	4620	4273	4511	Prairie Club - 18	\N	t	2025-06-24 19:48:53.499999-05	2025-06-24 19:48:53.499999-05	Series 18
13799	4620	4277	4511	Prairie Club - 20	\N	t	2025-06-24 19:48:53.499999-05	2025-06-24 19:48:53.499999-05	Series 20
13800	4620	4281	4511	Prairie Club - 23	\N	t	2025-06-24 19:48:53.499999-05	2025-06-24 19:48:53.499999-05	Series 23
13801	4620	4289	4511	Prairie Club - 28	\N	t	2025-06-24 19:48:53.499999-05	2025-06-24 19:48:53.499999-05	Series 28
13802	4620	4299	4511	Prairie Club - 33	\N	t	2025-06-24 19:48:53.499999-05	2025-06-24 19:48:53.499999-05	Series 33
13803	4620	4301	4511	Prairie Club - 35	\N	t	2025-06-24 19:48:53.499999-05	2025-06-24 19:48:53.499999-05	Series 35
13804	4620	4302	4511	Prairie Club - 36	\N	t	2025-06-24 19:48:53.499999-05	2025-06-24 19:48:53.499999-05	Series 36
13805	4620	4305	4511	Prairie Club - 39	\N	t	2025-06-24 19:48:53.499999-05	2025-06-24 19:48:53.499999-05	Series 39
13806	4620	4320	4511	Prairie Club - 9	\N	t	2025-06-24 19:48:53.499999-05	2025-06-24 19:48:53.499999-05	Series 9
13807	4620	4363	4511	Prairie Club - 9 (Division 9)	\N	t	2025-06-24 19:48:53.499999-05	2025-06-24 19:48:53.499999-05	Series 9 (Division 9)
13808	4620	4384	4513	Prairie Club 2a	\N	t	2025-06-24 19:48:53.499999-05	2025-06-24 19:48:53.499999-05	S2
13809	4621	4270	4511	Prairie Club I - 16	\N	t	2025-06-24 19:48:53.499999-05	2025-06-24 19:48:53.499999-05	Series 16
13810	4621	4284	4511	Prairie Club I - 25	\N	t	2025-06-24 19:48:53.499999-05	2025-06-24 19:48:53.499999-05	Series 25
13811	4621	4296	4511	Prairie Club I - 30	\N	t	2025-06-24 19:48:53.499999-05	2025-06-24 19:48:53.499999-05	Series 30
13812	4621	4298	4511	Prairie Club I - 32	\N	t	2025-06-24 19:48:53.499999-05	2025-06-24 19:48:53.499999-05	Series 32
13813	4621	4300	4511	Prairie Club I - 34	\N	t	2025-06-24 19:48:53.499999-05	2025-06-24 19:48:53.499999-05	Series 34
13814	4622	4270	4511	Prairie Club II - 16	\N	t	2025-06-24 19:48:53.499999-05	2025-06-24 19:48:53.499999-05	Series 16
13815	4622	4284	4511	Prairie Club II - 25	\N	t	2025-06-24 19:48:53.499999-05	2025-06-24 19:48:53.499999-05	Series 25
13816	4622	4296	4511	Prairie Club II - 30	\N	t	2025-06-24 19:48:53.499999-05	2025-06-24 19:48:53.499999-05	Series 30
13817	4622	4298	4511	Prairie Club II - 32	\N	t	2025-06-24 19:48:53.499999-05	2025-06-24 19:48:53.499999-05	Series 32
13818	4622	4300	4511	Prairie Club II - 34	\N	t	2025-06-24 19:48:53.499999-05	2025-06-24 19:48:53.499999-05	Series 34
13819	4623	4391	4514	Ravinia Green S2B	\N	t	2025-06-24 19:48:53.499999-05	2025-06-24 19:48:53.499999-05	Series 2B
13820	4624	4397	4513	River Forest 4	\N	t	2025-06-24 19:48:53.499999-05	2025-06-24 19:48:53.499999-05	S4
13821	4625	4387	4511	River Forest CC - 25 SW	\N	t	2025-06-24 19:48:53.499999-05	2025-06-24 19:48:53.499999-05	Series 25 SW
13822	4625	4388	4511	River Forest CC - 27 SW	\N	t	2025-06-24 19:48:53.499999-05	2025-06-24 19:48:53.499999-05	Series 27 SW
13823	4625	4389	4511	River Forest CC - 29 SW	\N	t	2025-06-24 19:48:53.499999-05	2025-06-24 19:48:53.499999-05	Series 29 SW
13824	4626	4306	4511	River Forest PD - 4	\N	t	2025-06-24 19:48:53.499999-05	2025-06-24 19:48:53.499999-05	Series 4
13825	4626	4379	4511	River Forest PD - 15 SW	\N	t	2025-06-24 19:48:53.499999-05	2025-06-24 19:48:53.499999-05	Series 15 SW
13826	4626	4385	4511	River Forest PD - 21 SW	\N	t	2025-06-24 19:48:53.499999-05	2025-06-24 19:48:53.499999-05	Series 21 SW
13827	4626	4387	4511	River Forest PD - 25 SW	\N	t	2025-06-24 19:48:53.499999-05	2025-06-24 19:48:53.499999-05	Series 25 SW
13828	4626	4410	4511	River Forest PD - 7 SW	\N	t	2025-06-24 19:48:53.499999-05	2025-06-24 19:48:53.499999-05	Series 7 SW
13829	4626	4413	4511	River Forest PD - 9 SW	\N	t	2025-06-24 19:48:53.499999-05	2025-06-24 19:48:53.499999-05	Series 9 SW
13830	4627	4376	4511	River Forest PD I - 13 SW	\N	t	2025-06-24 19:48:53.499999-05	2025-06-24 19:48:53.499999-05	Series 13 SW
13831	4628	4376	4511	River Forest PD II - 13 SW	\N	t	2025-06-24 19:48:53.499999-05	2025-06-24 19:48:53.499999-05	Series 13 SW
13832	4629	4305	4511	Royal Melbourne - 39	\N	t	2025-06-24 19:48:53.499999-05	2025-06-24 19:48:53.499999-05	Series 39
13833	4630	4292	4511	Ruth Lake - 3	\N	t	2025-06-24 19:48:53.499999-05	2025-06-24 19:48:53.499999-05	Series 3
13834	4630	4373	4511	Ruth Lake - 11 SW	\N	t	2025-06-24 19:48:53.499999-05	2025-06-24 19:48:53.499999-05	Series 11 SW
13835	4630	4376	4511	Ruth Lake - 13 SW	\N	t	2025-06-24 19:48:53.499999-05	2025-06-24 19:48:53.499999-05	Series 13 SW
13836	4630	4379	4511	Ruth Lake - 15 SW	\N	t	2025-06-24 19:48:53.499999-05	2025-06-24 19:48:53.499999-05	Series 15 SW
13837	4630	4382	4511	Ruth Lake - 17 SW	\N	t	2025-06-24 19:48:53.499999-05	2025-06-24 19:48:53.499999-05	Series 17 SW
13838	4630	4383	4511	Ruth Lake - 19 SW	\N	t	2025-06-24 19:48:53.499999-05	2025-06-24 19:48:53.499999-05	Series 19 SW
13839	4630	4385	4511	Ruth Lake - 21 SW	\N	t	2025-06-24 19:48:53.499999-05	2025-06-24 19:48:53.499999-05	Series 21 SW
13840	4630	4387	4511	Ruth Lake - 25 SW	\N	t	2025-06-24 19:48:53.499999-05	2025-06-24 19:48:53.499999-05	Series 25 SW
13841	4630	4388	4511	Ruth Lake - 27 SW	\N	t	2025-06-24 19:48:53.499999-05	2025-06-24 19:48:53.499999-05	Series 27 SW
13842	4630	4389	4511	Ruth Lake - 29 SW	\N	t	2025-06-24 19:48:53.499999-05	2025-06-24 19:48:53.499999-05	Series 29 SW
13843	4630	4410	4511	Ruth Lake - 7 SW	\N	t	2025-06-24 19:48:53.499999-05	2025-06-24 19:48:53.499999-05	Series 7 SW
13844	4631	4270	4511	Saddle & Cycle - 16	\N	t	2025-06-24 19:48:53.499999-05	2025-06-24 19:48:53.499999-05	Series 16
13845	4631	4280	4511	Saddle & Cycle - 22	\N	t	2025-06-24 19:48:53.499999-05	2025-06-24 19:48:53.499999-05	Series 22
13846	4631	4292	4511	Saddle & Cycle - 3	\N	t	2025-06-24 19:48:53.499999-05	2025-06-24 19:48:53.499999-05	Series 3
13847	4631	4298	4511	Saddle & Cycle - 32	\N	t	2025-06-24 19:48:53.499999-05	2025-06-24 19:48:53.499999-05	Series 32
13848	4631	4319	4511	Saddle & Cycle - 8	\N	t	2025-06-24 19:48:53.499999-05	2025-06-24 19:48:53.499999-05	Series 8
13849	4631	4370	4513	Saddle & Cycle 1	\N	t	2025-06-24 19:48:53.499999-05	2025-06-24 19:48:53.499999-05	S1
13850	4631	4374	4513	Saddle & Cycle 12	\N	t	2025-06-24 19:48:53.499999-05	2025-06-24 19:48:53.499999-05	S12
13851	4631	4397	4513	Saddle & Cycle 4	\N	t	2025-06-24 19:48:53.499999-05	2025-06-24 19:48:53.499999-05	S4
13852	4631	4409	4513	Saddle & Cycle 7	\N	t	2025-06-24 19:48:53.499999-05	2025-06-24 19:48:53.499999-05	S7
13853	4632	4276	4511	Salt Creek - 2	\N	t	2025-06-24 19:48:53.499999-05	2025-06-24 19:48:53.499999-05	Series 2
13854	4632	4306	4511	Salt Creek - 4	\N	t	2025-06-24 19:48:53.499999-05	2025-06-24 19:48:53.499999-05	Series 4
13855	4632	4376	4511	Salt Creek - 13 SW	\N	t	2025-06-24 19:48:53.499999-05	2025-06-24 19:48:53.499999-05	Series 13 SW
13856	4632	4379	4511	Salt Creek - 15 SW	\N	t	2025-06-24 19:48:53.499999-05	2025-06-24 19:48:53.499999-05	Series 15 SW
13857	4632	4382	4511	Salt Creek - 17 SW	\N	t	2025-06-24 19:48:53.499999-05	2025-06-24 19:48:53.499999-05	Series 17 SW
13858	4632	4383	4511	Salt Creek - 19 SW	\N	t	2025-06-24 19:48:53.499999-05	2025-06-24 19:48:53.499999-05	Series 19 SW
13859	4632	4385	4511	Salt Creek - 21 SW	\N	t	2025-06-24 19:48:53.499999-05	2025-06-24 19:48:53.499999-05	Series 21 SW
13860	4632	4386	4511	Salt Creek - 23 SW	\N	t	2025-06-24 19:48:53.499999-05	2025-06-24 19:48:53.499999-05	Series 23 SW
13861	4632	4389	4511	Salt Creek - 29 SW	\N	t	2025-06-24 19:48:53.499999-05	2025-06-24 19:48:53.499999-05	Series 29 SW
13862	4632	4410	4511	Salt Creek - 7 SW	\N	t	2025-06-24 19:48:53.499999-05	2025-06-24 19:48:53.499999-05	Series 7 SW
13863	4633	4388	4511	Salt Creek I - 27 SW	\N	t	2025-06-24 19:48:53.499999-05	2025-06-24 19:48:53.499999-05	Series 27 SW
13864	4634	4388	4511	Salt Creek II - 27 SW	\N	t	2025-06-24 19:48:53.499999-05	2025-06-24 19:48:53.499999-05	Series 27 SW
13865	4635	4262	4511	Skokie - 11	\N	t	2025-06-24 19:48:53.499999-05	2025-06-24 19:48:53.499999-05	Series 11
13866	4635	4332	4511	Skokie - 11 (Division 11)	\N	t	2025-06-24 19:48:53.499999-05	2025-06-24 19:48:53.499999-05	Series 11 (Division 11)
13867	4635	4267	4511	Skokie - 14	\N	t	2025-06-24 19:48:53.499999-05	2025-06-24 19:48:53.499999-05	Series 14
13868	4635	4273	4511	Skokie - 18	\N	t	2025-06-24 19:48:53.499999-05	2025-06-24 19:48:53.499999-05	Series 18
13869	4635	4277	4511	Skokie - 20	\N	t	2025-06-24 19:48:53.499999-05	2025-06-24 19:48:53.499999-05	Series 20
13870	4635	4280	4511	Skokie - 22	\N	t	2025-06-24 19:48:53.499999-05	2025-06-24 19:48:53.499999-05	Series 22
13871	4635	4283	4511	Skokie - 24	\N	t	2025-06-24 19:48:53.499999-05	2025-06-24 19:48:53.499999-05	Series 24
13872	4635	4284	4511	Skokie - 25	\N	t	2025-06-24 19:48:53.499999-05	2025-06-24 19:48:53.499999-05	Series 25
13873	4635	4286	4511	Skokie - 26	\N	t	2025-06-24 19:48:53.499999-05	2025-06-24 19:48:53.499999-05	Series 26
13874	4635	4287	4511	Skokie - 27	\N	t	2025-06-24 19:48:53.499999-05	2025-06-24 19:48:53.499999-05	Series 27
13875	4635	4290	4511	Skokie - 29	\N	t	2025-06-24 19:48:53.499999-05	2025-06-24 19:48:53.499999-05	Series 29
13876	4635	4292	4511	Skokie - 3	\N	t	2025-06-24 19:48:53.499999-05	2025-06-24 19:48:53.499999-05	Series 3
13877	4635	4297	4511	Skokie - 31	\N	t	2025-06-24 19:48:53.499999-05	2025-06-24 19:48:53.499999-05	Series 31
13878	4635	4299	4511	Skokie - 33	\N	t	2025-06-24 19:48:53.499999-05	2025-06-24 19:48:53.499999-05	Series 33
13879	4635	4302	4511	Skokie - 36	\N	t	2025-06-24 19:48:53.499999-05	2025-06-24 19:48:53.499999-05	Series 36
13880	4635	4303	4511	Skokie - 37	\N	t	2025-06-24 19:48:53.499999-05	2025-06-24 19:48:53.499999-05	Series 37
13881	4635	4304	4511	Skokie - 38	\N	t	2025-06-24 19:48:53.499999-05	2025-06-24 19:48:53.499999-05	Series 38
13882	4635	4317	4511	Skokie - 7	\N	t	2025-06-24 19:48:53.499999-05	2025-06-24 19:48:53.499999-05	Series 7
13883	4635	4359	4511	Skokie - 7 (Division 7)	\N	t	2025-06-24 19:48:53.499999-05	2025-06-24 19:48:53.499999-05	Series 7 (Division 7)
13884	4635	4372	4513	Skokie 11	\N	t	2025-06-24 19:48:53.499999-05	2025-06-24 19:48:53.499999-05	S11
13885	4635	4375	4513	Skokie 13	\N	t	2025-06-24 19:48:53.499999-05	2025-06-24 19:48:53.499999-05	S13
13886	4635	4378	4513	Skokie 15	\N	t	2025-06-24 19:48:53.499999-05	2025-06-24 19:48:53.499999-05	S15
13887	4635	4384	4513	Skokie 2	\N	t	2025-06-24 19:48:53.499999-05	2025-06-24 19:48:53.499999-05	S2
13888	4635	4390	4514	Skokie S2A	\N	t	2025-06-24 19:48:53.499999-05	2025-06-24 19:48:53.499999-05	Series 2A
13889	4635	4392	4514	Skokie S3	\N	t	2025-06-24 19:48:53.499999-05	2025-06-24 19:48:53.499999-05	Series 3
13890	4635	4397	4513	Skokie 4	\N	t	2025-06-24 19:48:53.499999-05	2025-06-24 19:48:53.499999-05	S4
13891	4635	4411	4513	Skokie 8	\N	t	2025-06-24 19:48:53.499999-05	2025-06-24 19:48:53.499999-05	S8
13892	4635	4412	4513	Skokie 9	\N	t	2025-06-24 19:48:53.499999-05	2025-06-24 19:48:53.499999-05	S9
13893	4636	4261	4511	South Barrington - 10	\N	t	2025-06-24 19:48:53.499999-05	2025-06-24 19:48:53.499999-05	Series 10
13894	4636	4267	4511	South Barrington - 14	\N	t	2025-06-24 19:48:53.499999-05	2025-06-24 19:48:53.499999-05	Series 14
13895	4636	4277	4511	South Barrington - 20	\N	t	2025-06-24 19:48:53.499999-05	2025-06-24 19:48:53.499999-05	Series 20
13896	4636	4287	4511	South Barrington - 27	\N	t	2025-06-24 19:48:53.499999-05	2025-06-24 19:48:53.499999-05	Series 27
13897	4636	4303	4511	South Barrington - 37	\N	t	2025-06-24 19:48:53.499999-05	2025-06-24 19:48:53.499999-05	Series 37
13898	4636	4306	4511	South Barrington - 4	\N	t	2025-06-24 19:48:53.499999-05	2025-06-24 19:48:53.499999-05	Series 4
13899	4636	4316	4511	South Barrington - 6	\N	t	2025-06-24 19:48:53.499999-05	2025-06-24 19:48:53.499999-05	Series 6
13900	4636	4358	4511	South Barrington - 6 (Division 6)	\N	t	2025-06-24 19:48:53.499999-05	2025-06-24 19:48:53.499999-05	Series 6 (Division 6)
13901	4637	4262	4511	Sunset Ridge - 11	\N	t	2025-06-24 19:48:53.499999-05	2025-06-24 19:48:53.499999-05	Series 11
13902	4637	4332	4511	Sunset Ridge - 11 (Division 11)	\N	t	2025-06-24 19:48:53.499999-05	2025-06-24 19:48:53.499999-05	Series 11 (Division 11)
13903	4637	4265	4511	Sunset Ridge - 13	\N	t	2025-06-24 19:48:53.499999-05	2025-06-24 19:48:53.499999-05	Series 13
13904	4637	4334	4511	Sunset Ridge - 13 (Division 13)	\N	t	2025-06-24 19:48:53.499999-05	2025-06-24 19:48:53.499999-05	Series 13 (Division 13)
13905	4637	4271	4511	Sunset Ridge - 17	\N	t	2025-06-24 19:48:53.499999-05	2025-06-24 19:48:53.499999-05	Series 17
13906	4637	4342	4511	Sunset Ridge - 17 (Division 17)	\N	t	2025-06-24 19:48:53.499999-05	2025-06-24 19:48:53.499999-05	Series 17 (Division 17)
13907	4637	4274	4511	Sunset Ridge - 19	\N	t	2025-06-24 19:48:53.499999-05	2025-06-24 19:48:53.499999-05	Series 19
13908	4637	4343	4511	Sunset Ridge - 19 (Division 19)	\N	t	2025-06-24 19:48:53.499999-05	2025-06-24 19:48:53.499999-05	Series 19 (Division 19)
13909	4637	4276	4511	Sunset Ridge - 2	\N	t	2025-06-24 19:48:53.499999-05	2025-06-24 19:48:53.499999-05	Series 2
13910	4637	4278	4511	Sunset Ridge - 21	\N	t	2025-06-24 19:48:53.499999-05	2025-06-24 19:48:53.499999-05	Series 21
13911	4637	4283	4511	Sunset Ridge - 24	\N	t	2025-06-24 19:48:53.499999-05	2025-06-24 19:48:53.499999-05	Series 24
13912	4637	4286	4511	Sunset Ridge - 26	\N	t	2025-06-24 19:48:53.499999-05	2025-06-24 19:48:53.499999-05	Series 26
13913	4637	4289	4511	Sunset Ridge - 28	\N	t	2025-06-24 19:48:53.499999-05	2025-06-24 19:48:53.499999-05	Series 28
13914	4637	4299	4511	Sunset Ridge - 33	\N	t	2025-06-24 19:48:53.499999-05	2025-06-24 19:48:53.499999-05	Series 33
13915	4637	4304	4511	Sunset Ridge - 38	\N	t	2025-06-24 19:48:53.499999-05	2025-06-24 19:48:53.499999-05	Series 38
13916	4637	4305	4511	Sunset Ridge - 39	\N	t	2025-06-24 19:48:53.499999-05	2025-06-24 19:48:53.499999-05	Series 39
13917	4637	4316	4511	Sunset Ridge - 6	\N	t	2025-06-24 19:48:53.499999-05	2025-06-24 19:48:53.499999-05	Series 6
13918	4637	4358	4511	Sunset Ridge - 6 (Division 6)	\N	t	2025-06-24 19:48:53.499999-05	2025-06-24 19:48:53.499999-05	Series 6 (Division 6)
13919	4637	4319	4511	Sunset Ridge - 8	\N	t	2025-06-24 19:48:53.499999-05	2025-06-24 19:48:53.499999-05	Series 8
13920	4637	4370	4513	Sunset Ridge 1	\N	t	2025-06-24 19:48:53.499999-05	2025-06-24 19:48:53.499999-05	S1
13921	4637	4371	4513	Sunset Ridge 10	\N	t	2025-06-24 19:48:53.499999-05	2025-06-24 19:48:53.499999-05	S10
13922	4637	4375	4513	Sunset Ridge 13	\N	t	2025-06-24 19:48:53.499999-05	2025-06-24 19:48:53.499999-05	S13
13923	4637	4407	4513	Sunset Ridge 5a	\N	t	2025-06-24 19:48:53.499999-05	2025-06-24 19:48:53.499999-05	S5
13924	4637	4409	4513	Sunset Ridge 7	\N	t	2025-06-24 19:48:53.499999-05	2025-06-24 19:48:53.499999-05	S7
13925	4638	4262	4511	Tennaqua - 11	\N	t	2025-06-24 19:48:53.499999-05	2025-06-24 19:48:53.499999-05	Series 11
13926	4638	4332	4511	Tennaqua - 11 (Division 11)	\N	t	2025-06-24 19:48:53.499999-05	2025-06-24 19:48:53.499999-05	Series 11 (Division 11)
13927	4638	4265	4511	Tennaqua - 13	\N	t	2025-06-24 19:48:53.499999-05	2025-06-24 19:48:53.499999-05	Series 13
13928	4638	4334	4511	Tennaqua - 13 (Division 13)	\N	t	2025-06-24 19:48:53.499999-05	2025-06-24 19:48:53.499999-05	Series 13 (Division 13)
13929	4638	4268	4511	Tennaqua - 15	\N	t	2025-06-24 19:48:53.499999-05	2025-06-24 19:48:53.499999-05	Series 15
13930	4638	4338	4511	Tennaqua - 15 (Division 15)	\N	t	2025-06-24 19:48:53.499999-05	2025-06-24 19:48:53.499999-05	Series 15 (Division 15)
13931	4638	4271	4511	Tennaqua - 17	\N	t	2025-06-24 19:48:53.499999-05	2025-06-24 19:48:53.499999-05	Series 17
13932	4638	4342	4511	Tennaqua - 17 (Division 17)	\N	t	2025-06-24 19:48:53.499999-05	2025-06-24 19:48:53.499999-05	Series 17 (Division 17)
13933	4638	4274	4511	Tennaqua - 19	\N	t	2025-06-24 19:48:53.499999-05	2025-06-24 19:48:53.499999-05	Series 19
13934	4638	4343	4511	Tennaqua - 19 (Division 19)	\N	t	2025-06-24 19:48:53.499999-05	2025-06-24 19:48:53.499999-05	Series 19 (Division 19)
13935	4638	4278	4511	Tennaqua - 21	\N	t	2025-06-24 19:48:53.499999-05	2025-06-24 19:48:53.499999-05	Series 21
13936	4638	4280	4511	Tennaqua - 22	\N	t	2025-06-24 19:48:53.499999-05	2025-06-24 19:48:53.499999-05	Series 22
13937	4638	4281	4511	Tennaqua - 23	\N	t	2025-06-24 19:48:53.499999-05	2025-06-24 19:48:53.499999-05	Series 23
13938	4638	4287	4511	Tennaqua - 27	\N	t	2025-06-24 19:48:53.499999-05	2025-06-24 19:48:53.499999-05	Series 27
13939	4638	4290	4511	Tennaqua - 29	\N	t	2025-06-24 19:48:53.499999-05	2025-06-24 19:48:53.499999-05	Series 29
13940	4638	4297	4511	Tennaqua - 31	\N	t	2025-06-24 19:48:53.499999-05	2025-06-24 19:48:53.499999-05	Series 31
13941	4638	4299	4511	Tennaqua - 33	\N	t	2025-06-24 19:48:53.499999-05	2025-06-24 19:48:53.499999-05	Series 33
13942	4638	4301	4511	Tennaqua - 35	\N	t	2025-06-24 19:48:53.499999-05	2025-06-24 19:48:53.499999-05	Series 35
13943	4638	4303	4511	Tennaqua - 37	\N	t	2025-06-24 19:48:53.499999-05	2025-06-24 19:48:53.499999-05	Series 37
13944	4638	4304	4511	Tennaqua - 38	\N	t	2025-06-24 19:48:53.499999-05	2025-06-24 19:48:53.499999-05	Series 38
13945	4638	4316	4511	Tennaqua - 6	\N	t	2025-06-24 19:48:53.499999-05	2025-06-24 19:48:53.499999-05	Series 6
13946	4638	4358	4511	Tennaqua - 6 (Division 6)	\N	t	2025-06-24 19:48:53.499999-05	2025-06-24 19:48:53.499999-05	Series 6 (Division 6)
13947	4638	4317	4511	Tennaqua - 7	\N	t	2025-06-24 19:48:53.499999-05	2025-06-24 19:48:53.499999-05	Series 7
13948	4638	4359	4511	Tennaqua - 7 (Division 7)	\N	t	2025-06-24 19:48:53.499999-05	2025-06-24 19:48:53.499999-05	Series 7 (Division 7)
13949	4638	4320	4511	Tennaqua - 9	\N	t	2025-06-24 19:48:53.499999-05	2025-06-24 19:48:53.499999-05	Series 9
13950	4638	4363	4511	Tennaqua - 9 (Division 9)	\N	t	2025-06-24 19:48:53.499999-05	2025-06-24 19:48:53.499999-05	Series 9 (Division 9)
13951	4638	4370	4514	Tennaqua S1	\N	t	2025-06-24 19:48:53.499999-05	2025-06-24 19:48:53.499999-05	Series 1
13952	4638	4371	4513	Tennaqua 10	\N	t	2025-06-24 19:48:53.499999-05	2025-06-24 19:48:53.499999-05	S10
13953	4638	4374	4513	Tennaqua 12	\N	t	2025-06-24 19:48:53.499999-05	2025-06-24 19:48:53.499999-05	S12
13954	4638	4380	4513	Tennaqua 16	\N	t	2025-06-24 19:48:53.499999-05	2025-06-24 19:48:53.499999-05	S16
13955	4638	4390	4514	Tennaqua S2A	\N	t	2025-06-24 19:48:53.499999-05	2025-06-24 19:48:53.499999-05	Series 2A
13956	4638	4391	4514	Tennaqua S2B	\N	t	2025-06-24 19:48:53.499999-05	2025-06-24 19:48:53.499999-05	Series 2B
13957	4638	4392	4513	Tennaqua 3	\N	t	2025-06-24 19:48:53.499999-05	2025-06-24 19:48:53.499999-05	S3
13958	4638	4392	4514	Tennaqua S3	\N	t	2025-06-24 19:48:53.499999-05	2025-06-24 19:48:53.499999-05	Series 3
13959	4638	4409	4513	Tennaqua 7	\N	t	2025-06-24 19:48:53.499999-05	2025-06-24 19:48:53.499999-05	S7
13960	4638	4412	4513	Tennaqua 9	\N	t	2025-06-24 19:48:53.499999-05	2025-06-24 19:48:53.499999-05	S9
13961	4639	4261	4511	Valley Lo - 10	\N	t	2025-06-24 19:48:53.499999-05	2025-06-24 19:48:53.499999-05	Series 10
13962	4639	4264	4511	Valley Lo - 12	\N	t	2025-06-24 19:48:53.499999-05	2025-06-24 19:48:53.499999-05	Series 12
13963	4639	4268	4511	Valley Lo - 15	\N	t	2025-06-24 19:48:53.499999-05	2025-06-24 19:48:53.499999-05	Series 15
13964	4639	4338	4511	Valley Lo - 15 (Division 15)	\N	t	2025-06-24 19:48:53.499999-05	2025-06-24 19:48:53.499999-05	Series 15 (Division 15)
13965	4639	4271	4511	Valley Lo - 17	\N	t	2025-06-24 19:48:53.499999-05	2025-06-24 19:48:53.499999-05	Series 17
13966	4639	4342	4511	Valley Lo - 17 (Division 17)	\N	t	2025-06-24 19:48:53.499999-05	2025-06-24 19:48:53.499999-05	Series 17 (Division 17)
13967	4639	4273	4511	Valley Lo - 18	\N	t	2025-06-24 19:48:53.499999-05	2025-06-24 19:48:53.499999-05	Series 18
13968	4639	4276	4511	Valley Lo - 2	\N	t	2025-06-24 19:48:53.499999-05	2025-06-24 19:48:53.499999-05	Series 2
13969	4639	4277	4511	Valley Lo - 20	\N	t	2025-06-24 19:48:53.499999-05	2025-06-24 19:48:53.499999-05	Series 20
13970	4639	4280	4511	Valley Lo - 22	\N	t	2025-06-24 19:48:53.499999-05	2025-06-24 19:48:53.499999-05	Series 22
13971	4639	4281	4511	Valley Lo - 23	\N	t	2025-06-24 19:48:53.499999-05	2025-06-24 19:48:53.499999-05	Series 23
13972	4639	4283	4511	Valley Lo - 24	\N	t	2025-06-24 19:48:53.499999-05	2025-06-24 19:48:53.499999-05	Series 24
13973	4639	4284	4511	Valley Lo - 25	\N	t	2025-06-24 19:48:53.499999-05	2025-06-24 19:48:53.499999-05	Series 25
13974	4639	4286	4511	Valley Lo - 26	\N	t	2025-06-24 19:48:53.499999-05	2025-06-24 19:48:53.499999-05	Series 26
13975	4639	4289	4511	Valley Lo - 28	\N	t	2025-06-24 19:48:53.499999-05	2025-06-24 19:48:53.499999-05	Series 28
13976	4639	4297	4511	Valley Lo - 31	\N	t	2025-06-24 19:48:53.499999-05	2025-06-24 19:48:53.499999-05	Series 31
13977	4639	4299	4511	Valley Lo - 33	\N	t	2025-06-24 19:48:53.499999-05	2025-06-24 19:48:53.499999-05	Series 33
13978	4639	4300	4511	Valley Lo - 34	\N	t	2025-06-24 19:48:53.499999-05	2025-06-24 19:48:53.499999-05	Series 34
13979	4639	4303	4511	Valley Lo - 37	\N	t	2025-06-24 19:48:53.499999-05	2025-06-24 19:48:53.499999-05	Series 37
13980	4639	4305	4511	Valley Lo - 39	\N	t	2025-06-24 19:48:53.499999-05	2025-06-24 19:48:53.499999-05	Series 39
13981	4639	4316	4511	Valley Lo - 6	\N	t	2025-06-24 19:48:53.499999-05	2025-06-24 19:48:53.499999-05	Series 6
13982	4639	4358	4511	Valley Lo - 6 (Division 6)	\N	t	2025-06-24 19:48:53.499999-05	2025-06-24 19:48:53.499999-05	Series 6 (Division 6)
13983	4639	4319	4511	Valley Lo - 8	\N	t	2025-06-24 19:48:53.499999-05	2025-06-24 19:48:53.499999-05	Series 8
13984	4639	4372	4513	Valley Lo 11	\N	t	2025-06-24 19:48:53.499999-05	2025-06-24 19:48:53.499999-05	S11
13985	4639	4380	4513	Valley Lo 16	\N	t	2025-06-24 19:48:53.499999-05	2025-06-24 19:48:53.499999-05	S16
13986	4639	4384	4513	Valley Lo 2	\N	t	2025-06-24 19:48:53.499999-05	2025-06-24 19:48:53.499999-05	S2
13987	4639	4392	4514	Valley Lo S3	\N	t	2025-06-24 19:48:53.499999-05	2025-06-24 19:48:53.499999-05	Series 3
13988	4639	4397	4513	Valley Lo 4	\N	t	2025-06-24 19:48:53.499999-05	2025-06-24 19:48:53.499999-05	S4
13989	4639	4408	4513	Valley Lo 6	\N	t	2025-06-24 19:48:53.499999-05	2025-06-24 19:48:53.499999-05	S6
13990	4639	4411	4513	Valley Lo 8	\N	t	2025-06-24 19:48:53.499999-05	2025-06-24 19:48:53.499999-05	S8
13991	4640	4261	4511	Westmoreland - 10	\N	t	2025-06-24 19:48:53.499999-05	2025-06-24 19:48:53.499999-05	Series 10
13992	4640	4264	4511	Westmoreland - 12	\N	t	2025-06-24 19:48:53.499999-05	2025-06-24 19:48:53.499999-05	Series 12
13993	4640	4267	4511	Westmoreland - 14	\N	t	2025-06-24 19:48:53.499999-05	2025-06-24 19:48:53.499999-05	Series 14
13994	4640	4273	4511	Westmoreland - 18	\N	t	2025-06-24 19:48:53.499999-05	2025-06-24 19:48:53.499999-05	Series 18
13995	4640	4276	4511	Westmoreland - 2	\N	t	2025-06-24 19:48:53.499999-05	2025-06-24 19:48:53.499999-05	Series 2
13996	4640	4277	4511	Westmoreland - 20	\N	t	2025-06-24 19:48:53.499999-05	2025-06-24 19:48:53.499999-05	Series 20
13997	4640	4283	4511	Westmoreland - 24	\N	t	2025-06-24 19:48:53.499999-05	2025-06-24 19:48:53.499999-05	Series 24
13998	4640	4286	4511	Westmoreland - 26	\N	t	2025-06-24 19:48:53.499999-05	2025-06-24 19:48:53.499999-05	Series 26
13999	4640	4290	4511	Westmoreland - 29	\N	t	2025-06-24 19:48:53.499999-05	2025-06-24 19:48:53.499999-05	Series 29
14000	4640	4297	4511	Westmoreland - 31	\N	t	2025-06-24 19:48:53.499999-05	2025-06-24 19:48:53.499999-05	Series 31
14001	4640	4303	4511	Westmoreland - 37	\N	t	2025-06-24 19:48:53.499999-05	2025-06-24 19:48:53.499999-05	Series 37
14002	4640	4305	4511	Westmoreland - 39	\N	t	2025-06-24 19:48:53.499999-05	2025-06-24 19:48:53.499999-05	Series 39
14003	4640	4306	4511	Westmoreland - 4	\N	t	2025-06-24 19:48:53.499999-05	2025-06-24 19:48:53.499999-05	Series 4
14004	4640	4317	4511	Westmoreland - 7	\N	t	2025-06-24 19:48:53.499999-05	2025-06-24 19:48:53.499999-05	Series 7
14005	4640	4359	4511	Westmoreland - 7 (Division 7)	\N	t	2025-06-24 19:48:53.499999-05	2025-06-24 19:48:53.499999-05	Series 7 (Division 7)
14006	4640	4319	4511	Westmoreland - 8	\N	t	2025-06-24 19:48:53.499999-05	2025-06-24 19:48:53.499999-05	Series 8
14007	4640	4372	4513	Westmoreland 11	\N	t	2025-06-24 19:48:53.499999-05	2025-06-24 19:48:53.499999-05	S11
14008	4640	4375	4513	Westmoreland 13	\N	t	2025-06-24 19:48:53.499999-05	2025-06-24 19:48:53.499999-05	S13
14009	4640	4377	4513	Westmoreland 14	\N	t	2025-06-24 19:48:53.499999-05	2025-06-24 19:48:53.499999-05	S14
14010	4640	4392	4513	Westmoreland 3	\N	t	2025-06-24 19:48:53.499999-05	2025-06-24 19:48:53.499999-05	S3
14011	4640	4397	4513	Westmoreland 4	\N	t	2025-06-24 19:48:53.499999-05	2025-06-24 19:48:53.499999-05	S4
14012	4640	4408	4513	Westmoreland 6	\N	t	2025-06-24 19:48:53.499999-05	2025-06-24 19:48:53.499999-05	S6
14013	4640	4412	4513	Westmoreland 9	\N	t	2025-06-24 19:48:53.499999-05	2025-06-24 19:48:53.499999-05	S9
14014	4640	4414	4514	Westmoreland	\N	t	2025-06-24 19:48:53.499999-05	2025-06-24 19:48:53.499999-05	SA
14015	4641	4382	4511	White Eagle - 17 SW	\N	t	2025-06-24 19:48:53.499999-05	2025-06-24 19:48:53.499999-05	Series 17 SW
14016	4641	4386	4511	White Eagle - 23 SW	\N	t	2025-06-24 19:48:53.499999-05	2025-06-24 19:48:53.499999-05	Series 23 SW
14017	4641	4387	4511	White Eagle - 25 SW	\N	t	2025-06-24 19:48:53.499999-05	2025-06-24 19:48:53.499999-05	Series 25 SW
14018	4641	4389	4511	White Eagle - 29 SW	\N	t	2025-06-24 19:48:53.499999-05	2025-06-24 19:48:53.499999-05	Series 29 SW
14019	4642	4370	4514	Wilmette S1 T1	\N	t	2025-06-24 19:48:53.499999-05	2025-06-24 19:48:53.499999-05	Series 1 T1
14020	4642	4371	4513	Wilmette 10	\N	t	2025-06-24 19:48:53.499999-05	2025-06-24 19:48:53.499999-05	S10
14021	4642	4372	4513	Wilmette 11	\N	t	2025-06-24 19:48:53.499999-05	2025-06-24 19:48:53.499999-05	S11
14022	4642	4378	4513	Wilmette 15	\N	t	2025-06-24 19:48:53.499999-05	2025-06-24 19:48:53.499999-05	S15
14023	4642	4380	4513	Wilmette 16a	\N	t	2025-06-24 19:48:53.499999-05	2025-06-24 19:48:53.499999-05	S16
14024	4642	4381	4513	Wilmette 17	\N	t	2025-06-24 19:48:53.499999-05	2025-06-24 19:48:53.499999-05	S17
14025	4642	4391	4514	Wilmette S2B	\N	t	2025-06-24 19:48:53.499999-05	2025-06-24 19:48:53.499999-05	Series 2B
14026	4642	4392	4513	Wilmette 3	\N	t	2025-06-24 19:48:53.499999-05	2025-06-24 19:48:53.499999-05	S3
14027	4642	4397	4513	Wilmette 4	\N	t	2025-06-24 19:48:53.499999-05	2025-06-24 19:48:53.499999-05	S4
14028	4642	4407	4513	Wilmette 5	\N	t	2025-06-24 19:48:53.499999-05	2025-06-24 19:48:53.499999-05	S5
14029	4642	4411	4513	Wilmette 8a	\N	t	2025-06-24 19:48:53.499999-05	2025-06-24 19:48:53.499999-05	S8
14030	4643	4260	4511	Wilmette PD - 1	\N	t	2025-06-24 19:48:53.499999-05	2025-06-24 19:48:53.499999-05	Series 1
14031	4643	4261	4511	Wilmette PD - 10	\N	t	2025-06-24 19:48:53.499999-05	2025-06-24 19:48:53.499999-05	Series 10
14032	4643	4264	4511	Wilmette PD - 12	\N	t	2025-06-24 19:48:53.499999-05	2025-06-24 19:48:53.499999-05	Series 12
14033	4643	4271	4511	Wilmette PD - 17	\N	t	2025-06-24 19:48:53.499999-05	2025-06-24 19:48:53.499999-05	Series 17
14034	4643	4342	4511	Wilmette PD - 17 (Division 17)	\N	t	2025-06-24 19:48:53.499999-05	2025-06-24 19:48:53.499999-05	Series 17 (Division 17)
14035	4643	4277	4511	Wilmette PD - 20	\N	t	2025-06-24 19:48:53.499999-05	2025-06-24 19:48:53.499999-05	Series 20
14036	4643	4283	4511	Wilmette PD - 24	\N	t	2025-06-24 19:48:53.499999-05	2025-06-24 19:48:53.499999-05	Series 24
14037	4643	4287	4511	Wilmette PD - 27	\N	t	2025-06-24 19:48:53.499999-05	2025-06-24 19:48:53.499999-05	Series 27
14038	4643	4290	4511	Wilmette PD - 29	\N	t	2025-06-24 19:48:53.499999-05	2025-06-24 19:48:53.499999-05	Series 29
14039	4643	4299	4511	Wilmette PD - 33	\N	t	2025-06-24 19:48:53.499999-05	2025-06-24 19:48:53.499999-05	Series 33
14040	4643	4301	4511	Wilmette PD - 35	\N	t	2025-06-24 19:48:53.499999-05	2025-06-24 19:48:53.499999-05	Series 35
14041	4643	4315	4511	Wilmette PD - 5	\N	t	2025-06-24 19:48:53.499999-05	2025-06-24 19:48:53.499999-05	Series 5
14042	4643	4319	4511	Wilmette PD - 8	\N	t	2025-06-24 19:48:53.499999-05	2025-06-24 19:48:53.499999-05	Series 8
14043	4644	4262	4511	Wilmette PD I - 11	\N	t	2025-06-24 19:48:53.499999-05	2025-06-24 19:48:53.499999-05	Series 11
14044	4644	4332	4511	Wilmette PD I - 11 (Division 11)	\N	t	2025-06-24 19:48:53.499999-05	2025-06-24 19:48:53.499999-05	Series 11 (Division 11)
14045	4644	4265	4511	Wilmette PD I - 13	\N	t	2025-06-24 19:48:53.499999-05	2025-06-24 19:48:53.499999-05	Series 13
14046	4644	4334	4511	Wilmette PD I - 13 (Division 13)	\N	t	2025-06-24 19:48:53.499999-05	2025-06-24 19:48:53.499999-05	Series 13 (Division 13)
14047	4644	4273	4511	Wilmette PD I - 18	\N	t	2025-06-24 19:48:53.499999-05	2025-06-24 19:48:53.499999-05	Series 18
14048	4644	4274	4511	Wilmette PD I - 19	\N	t	2025-06-24 19:48:53.499999-05	2025-06-24 19:48:53.499999-05	Series 19
14049	4644	4343	4511	Wilmette PD I - 19 (Division 19)	\N	t	2025-06-24 19:48:53.499999-05	2025-06-24 19:48:53.499999-05	Series 19 (Division 19)
14050	4644	4276	4511	Wilmette PD I - 2	\N	t	2025-06-24 19:48:53.499999-05	2025-06-24 19:48:53.499999-05	Series 2
14051	4644	4278	4511	Wilmette PD I - 21	\N	t	2025-06-24 19:48:53.499999-05	2025-06-24 19:48:53.499999-05	Series 21
14052	4644	4289	4511	Wilmette PD I - 28	\N	t	2025-06-24 19:48:53.499999-05	2025-06-24 19:48:53.499999-05	Series 28
14053	4644	4296	4511	Wilmette PD I - 30	\N	t	2025-06-24 19:48:53.499999-05	2025-06-24 19:48:53.499999-05	Series 30
14054	4644	4306	4511	Wilmette PD I - 4	\N	t	2025-06-24 19:48:53.499999-05	2025-06-24 19:48:53.499999-05	Series 4
14055	4645	4262	4511	Wilmette PD II - 11	\N	t	2025-06-24 19:48:53.499999-05	2025-06-24 19:48:53.499999-05	Series 11
14056	4645	4332	4511	Wilmette PD II - 11 (Division 11)	\N	t	2025-06-24 19:48:53.499999-05	2025-06-24 19:48:53.499999-05	Series 11 (Division 11)
14057	4645	4265	4511	Wilmette PD II - 13	\N	t	2025-06-24 19:48:53.499999-05	2025-06-24 19:48:53.499999-05	Series 13
14058	4645	4334	4511	Wilmette PD II - 13 (Division 13)	\N	t	2025-06-24 19:48:53.499999-05	2025-06-24 19:48:53.499999-05	Series 13 (Division 13)
14059	4645	4273	4511	Wilmette PD II - 18	\N	t	2025-06-24 19:48:53.499999-05	2025-06-24 19:48:53.499999-05	Series 18
14060	4645	4274	4511	Wilmette PD II - 19	\N	t	2025-06-24 19:48:53.499999-05	2025-06-24 19:48:53.499999-05	Series 19
14061	4645	4343	4511	Wilmette PD II - 19 (Division 19)	\N	t	2025-06-24 19:48:53.499999-05	2025-06-24 19:48:53.499999-05	Series 19 (Division 19)
14062	4645	4276	4511	Wilmette PD II - 2	\N	t	2025-06-24 19:48:53.499999-05	2025-06-24 19:48:53.499999-05	Series 2
14063	4645	4278	4511	Wilmette PD II - 21	\N	t	2025-06-24 19:48:53.499999-05	2025-06-24 19:48:53.499999-05	Series 21
14064	4645	4289	4511	Wilmette PD II - 28	\N	t	2025-06-24 19:48:53.499999-05	2025-06-24 19:48:53.499999-05	Series 28
14065	4645	4296	4511	Wilmette PD II - 30	\N	t	2025-06-24 19:48:53.499999-05	2025-06-24 19:48:53.499999-05	Series 30
14066	4645	4306	4511	Wilmette PD II - 4	\N	t	2025-06-24 19:48:53.499999-05	2025-06-24 19:48:53.499999-05	Series 4
14067	4646	4260	4511	Winnetka - 1	\N	t	2025-06-24 19:48:53.499999-05	2025-06-24 19:48:53.499999-05	Series 1
14068	4646	4261	4511	Winnetka - 10	\N	t	2025-06-24 19:48:53.499999-05	2025-06-24 19:48:53.499999-05	Series 10
14069	4646	4262	4511	Winnetka - 11	\N	t	2025-06-24 19:48:53.499999-05	2025-06-24 19:48:53.499999-05	Series 11
14070	4646	4332	4511	Winnetka - 11 (Division 11)	\N	t	2025-06-24 19:48:53.499999-05	2025-06-24 19:48:53.499999-05	Series 11 (Division 11)
14071	4646	4264	4511	Winnetka - 12	\N	t	2025-06-24 19:48:53.499999-05	2025-06-24 19:48:53.499999-05	Series 12
14072	4646	4265	4511	Winnetka - 13	\N	t	2025-06-24 19:48:53.499999-05	2025-06-24 19:48:53.499999-05	Series 13
14073	4646	4334	4511	Winnetka - 13 (Division 13)	\N	t	2025-06-24 19:48:53.499999-05	2025-06-24 19:48:53.499999-05	Series 13 (Division 13)
14074	4646	4267	4511	Winnetka - 14	\N	t	2025-06-24 19:48:53.499999-05	2025-06-24 19:48:53.499999-05	Series 14
14075	4646	4270	4511	Winnetka - 16	\N	t	2025-06-24 19:48:53.499999-05	2025-06-24 19:48:53.499999-05	Series 16
14076	4646	4273	4511	Winnetka - 18	\N	t	2025-06-24 19:48:53.499999-05	2025-06-24 19:48:53.499999-05	Series 18
14077	4646	4276	4511	Winnetka - 2	\N	t	2025-06-24 19:48:53.499999-05	2025-06-24 19:48:53.499999-05	Series 2
14078	4646	4278	4511	Winnetka - 21	\N	t	2025-06-24 19:48:53.499999-05	2025-06-24 19:48:53.499999-05	Series 21
14079	4646	4281	4511	Winnetka - 23	\N	t	2025-06-24 19:48:53.499999-05	2025-06-24 19:48:53.499999-05	Series 23
14080	4646	4283	4511	Winnetka - 24	\N	t	2025-06-24 19:48:53.499999-05	2025-06-24 19:48:53.499999-05	Series 24
14081	4646	4284	4511	Winnetka - 25	\N	t	2025-06-24 19:48:53.499999-05	2025-06-24 19:48:53.499999-05	Series 25
14082	4646	4286	4511	Winnetka - 26	\N	t	2025-06-24 19:48:53.499999-05	2025-06-24 19:48:53.499999-05	Series 26
14083	4646	4290	4511	Winnetka - 29	\N	t	2025-06-24 19:48:53.499999-05	2025-06-24 19:48:53.499999-05	Series 29
14084	4646	4292	4511	Winnetka - 3	\N	t	2025-06-24 19:48:53.499999-05	2025-06-24 19:48:53.499999-05	Series 3
14085	4646	4296	4511	Winnetka - 30	\N	t	2025-06-24 19:48:53.499999-05	2025-06-24 19:48:53.499999-05	Series 30
14086	4646	4297	4511	Winnetka - 31	\N	t	2025-06-24 19:48:53.499999-05	2025-06-24 19:48:53.499999-05	Series 31
14087	4646	4299	4511	Winnetka - 33	\N	t	2025-06-24 19:48:53.499999-05	2025-06-24 19:48:53.499999-05	Series 33
14088	4646	4302	4511	Winnetka - 36	\N	t	2025-06-24 19:48:53.499999-05	2025-06-24 19:48:53.499999-05	Series 36
14089	4646	4305	4511	Winnetka - 39	\N	t	2025-06-24 19:48:53.499999-05	2025-06-24 19:48:53.499999-05	Series 39
14090	4646	4306	4511	Winnetka - 4	\N	t	2025-06-24 19:48:53.499999-05	2025-06-24 19:48:53.499999-05	Series 4
14091	4646	4317	4511	Winnetka - 7	\N	t	2025-06-24 19:48:53.499999-05	2025-06-24 19:48:53.499999-05	Series 7
14092	4646	4359	4511	Winnetka - 7 (Division 7)	\N	t	2025-06-24 19:48:53.499999-05	2025-06-24 19:48:53.499999-05	Series 7 (Division 7)
14093	4646	4319	4511	Winnetka - 8	\N	t	2025-06-24 19:48:53.499999-05	2025-06-24 19:48:53.499999-05	Series 8
14094	4646	4320	4511	Winnetka - 9	\N	t	2025-06-24 19:48:53.499999-05	2025-06-24 19:48:53.499999-05	Series 9
14095	4646	4363	4511	Winnetka - 9 (Division 9)	\N	t	2025-06-24 19:48:53.499999-05	2025-06-24 19:48:53.499999-05	Series 9 (Division 9)
14096	4646	4370	4513	Winnetka 1	\N	t	2025-06-24 19:48:53.499999-05	2025-06-24 19:48:53.499999-05	S1
14097	4646	4374	4513	Winnetka 12	\N	t	2025-06-24 19:48:53.499999-05	2025-06-24 19:48:53.499999-05	S12
14098	4646	4375	4513	Winnetka 13	\N	t	2025-06-24 19:48:53.499999-05	2025-06-24 19:48:53.499999-05	S13
14099	4646	4378	4513	Winnetka 15	\N	t	2025-06-24 19:48:53.499999-05	2025-06-24 19:48:53.499999-05	S15
14100	4646	4380	4513	Winnetka 16	\N	t	2025-06-24 19:48:53.499999-05	2025-06-24 19:48:53.499999-05	S16
14101	4646	4391	4514	Winnetka S2B	\N	t	2025-06-24 19:48:53.499999-05	2025-06-24 19:48:53.499999-05	Series 2B
14102	4646	4407	4513	Winnetka 5a	\N	t	2025-06-24 19:48:53.499999-05	2025-06-24 19:48:53.499999-05	S5
14103	4646	4408	4513	Winnetka 6	\N	t	2025-06-24 19:48:53.499999-05	2025-06-24 19:48:53.499999-05	S6
14104	4646	4411	4513	Winnetka 8	\N	t	2025-06-24 19:48:53.499999-05	2025-06-24 19:48:53.499999-05	S8
14105	4646	4412	4513	Winnetka 9	\N	t	2025-06-24 19:48:53.499999-05	2025-06-24 19:48:53.499999-05	S9
14106	4647	4274	4511	Winnetka I - 19	\N	t	2025-06-24 19:48:53.499999-05	2025-06-24 19:48:53.499999-05	Series 19
14107	4647	4343	4511	Winnetka I - 19 (Division 19)	\N	t	2025-06-24 19:48:53.499999-05	2025-06-24 19:48:53.499999-05	Series 19 (Division 19)
14108	4647	4298	4511	Winnetka I - 32	\N	t	2025-06-24 19:48:53.499999-05	2025-06-24 19:48:53.499999-05	Series 32
14109	4647	4315	4511	Winnetka I - 5	\N	t	2025-06-24 19:48:53.499999-05	2025-06-24 19:48:53.499999-05	Series 5
14110	4647	4424	4513	Winnetka I	\N	t	2025-06-24 19:48:53.499999-05	2025-06-24 19:48:53.499999-05	SI
14111	4648	4274	4511	Winnetka II - 19	\N	t	2025-06-24 19:48:53.499999-05	2025-06-24 19:48:53.499999-05	Series 19
14112	4648	4343	4511	Winnetka II - 19 (Division 19)	\N	t	2025-06-24 19:48:53.499999-05	2025-06-24 19:48:53.499999-05	Series 19 (Division 19)
14113	4648	4298	4511	Winnetka II - 32	\N	t	2025-06-24 19:48:53.499999-05	2025-06-24 19:48:53.499999-05	Series 32
14114	4648	4315	4511	Winnetka II - 5	\N	t	2025-06-24 19:48:53.499999-05	2025-06-24 19:48:53.499999-05	Series 5
14115	4649	4261	4511	Winter Club - 10	\N	t	2025-06-24 19:48:53.499999-05	2025-06-24 19:48:53.499999-05	Series 10
14116	4649	4264	4511	Winter Club - 12	\N	t	2025-06-24 19:48:53.499999-05	2025-06-24 19:48:53.499999-05	Series 12
14117	4649	4265	4511	Winter Club - 13	\N	t	2025-06-24 19:48:53.499999-05	2025-06-24 19:48:53.499999-05	Series 13
14118	4649	4334	4511	Winter Club - 13 (Division 13)	\N	t	2025-06-24 19:48:53.499999-05	2025-06-24 19:48:53.499999-05	Series 13 (Division 13)
14119	4649	4271	4511	Winter Club - 17	\N	t	2025-06-24 19:48:53.499999-05	2025-06-24 19:48:53.499999-05	Series 17
14120	4649	4342	4511	Winter Club - 17 (Division 17)	\N	t	2025-06-24 19:48:53.499999-05	2025-06-24 19:48:53.499999-05	Series 17 (Division 17)
14121	4649	4277	4511	Winter Club - 20	\N	t	2025-06-24 19:48:53.499999-05	2025-06-24 19:48:53.499999-05	Series 20
14122	4649	4283	4511	Winter Club - 24	\N	t	2025-06-24 19:48:53.499999-05	2025-06-24 19:48:53.499999-05	Series 24
14123	4649	4286	4511	Winter Club - 26	\N	t	2025-06-24 19:48:53.499999-05	2025-06-24 19:48:53.499999-05	Series 26
14124	4649	4292	4511	Winter Club - 3	\N	t	2025-06-24 19:48:53.499999-05	2025-06-24 19:48:53.499999-05	Series 3
14125	4649	4300	4511	Winter Club - 34	\N	t	2025-06-24 19:48:53.499999-05	2025-06-24 19:48:53.499999-05	Series 34
14126	4649	4302	4511	Winter Club - 36	\N	t	2025-06-24 19:48:53.499999-05	2025-06-24 19:48:53.499999-05	Series 36
14127	4649	4304	4511	Winter Club - 38	\N	t	2025-06-24 19:48:53.499999-05	2025-06-24 19:48:53.499999-05	Series 38
14128	4649	4374	4513	Winter Club 12	\N	t	2025-06-24 19:48:53.499999-05	2025-06-24 19:48:53.499999-05	S12
14129	4649	4378	4513	Winter Club 15	\N	t	2025-06-24 19:48:53.499999-05	2025-06-24 19:48:53.499999-05	S15
14130	4649	4381	4513	Winter Club 17	\N	t	2025-06-24 19:48:53.499999-05	2025-06-24 19:48:53.499999-05	S17
14131	4649	4408	4513	Winter Club 6	\N	t	2025-06-24 19:48:53.499999-05	2025-06-24 19:48:53.499999-05	S6
\.


--
-- TOC entry 4174 (class 0 OID 46620)
-- Dependencies: 260
-- Data for Name: user_activity_logs; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.user_activity_logs (id, user_email, activity_type, page, action, details, ip_address, "timestamp") FROM stdin;
10449	rossfreedman@gmail.com	auth	\N	login	Login successful. 2 associated players	127.0.0.1	2025-06-24 07:02:12.679974-05
10450	rossfreedman@gmail.com	page_visit	mobile_home	\N	\N	127.0.0.1	2025-06-24 07:02:12.707227-05
10451	rossfreedman@gmail.com	page_visit	mobile_schedule_lesson	\N	\N	127.0.0.1	2025-06-24 07:03:38.448093-05
10452	rossfreedman@gmail.com	page_visit	mobile_home	\N	\N	127.0.0.1	2025-06-24 07:08:04.094559-05
10453	rossfreedman@gmail.com	page_visit	mobile_home	\N	\N	127.0.0.1	2025-06-24 07:08:29.954011-05
10454	rossfreedman@gmail.com	page_visit	admin	\N	\N	127.0.0.1	2025-06-24 07:08:37.66521-05
10455	rossfreedman@gmail.com	page_visit	admin_users	\N	\N	127.0.0.1	2025-06-24 07:08:38.608657-05
10456	rossfreedman@gmail.com	admin_action	\N	delete_user	Deleted user: Olga Martinsone (olga@gmail.com)	127.0.0.1	2025-06-24 07:08:46.532415-05
10457	rossfreedman@gmail.com	page_visit	mobile_home	\N	\N	127.0.0.1	2025-06-24 07:08:48.395867-05
10458	rossfreedman@gmail.com	page_visit	mobile_settings	\N	\N	127.0.0.1	2025-06-24 07:08:50.755999-05
10459	rossfreedman@gmail.com	page_visit	mobile_settings	\N	\N	127.0.0.1	2025-06-24 07:08:51.610254-05
10460	olga@gmail.com	auth	\N	register	Registration successful. Player association created with exact match and team assignment verified	127.0.0.1	2025-06-24 07:10:37.565351-05
10461	olga@gmail.com	page_visit	mobile_home	\N	\N	127.0.0.1	2025-06-24 07:10:37.596724-05
10462	olga@gmail.com	page_visit	mobile_availability	\N	\N	127.0.0.1	2025-06-24 07:10:40.957696-05
10463	olga@gmail.com	page_visit	mobile_home	\N	\N	127.0.0.1	2025-06-24 07:10:41.927644-05
10464	olga@gmail.com	page_visit	mobile_analyze_me	\N	\N	127.0.0.1	2025-06-24 07:10:44.615826-05
10465	olga@gmail.com	page_visit	mobile_home	\N	\N	127.0.0.1	2025-06-24 07:10:48.230329-05
10466	olga@gmail.com	page_visit	mobile_player_search	\N	\N	127.0.0.1	2025-06-24 07:10:50.769557-05
10467	olga@gmail.com	page_visit	mobile_player_search	\N	\N	127.0.0.1	2025-06-24 07:10:53.272961-05
10468	olga@gmail.com	page_visit	mobile_player_search	\N	\N	127.0.0.1	2025-06-24 07:10:56.798033-05
10469	olga@gmail.com	page_visit	mobile_player_search	\N	\N	127.0.0.1	2025-06-24 07:11:02.298055-05
10470	olga@gmail.com	player_search	\N	\N	Searched for first name "r", found 929 matches	127.0.0.1	2025-06-24 07:11:03.521809-05
10471	olga@gmail.com	page_visit	mobile_player_search	\N	\N	127.0.0.1	2025-06-24 07:11:03.523834-05
10472	olga@gmail.com	page_visit	mobile_home	\N	\N	127.0.0.1	2025-06-24 07:11:16.649199-05
10473	olga@gmail.com	page_visit	mobile_schedule_lesson	\N	\N	127.0.0.1	2025-06-24 07:11:21.200583-05
10474	olga@gmail.com	page_visit	mobile_schedule_lesson	\N	\N	127.0.0.1	2025-06-24 07:11:39.233669-05
10475	olga@gmail.com	page_visit	mobile_home	\N	\N	127.0.0.1	2025-06-24 07:12:55.988015-05
10476	olga@gmail.com	page_visit	mobile_schedule_lesson	\N	\N	127.0.0.1	2025-06-24 07:12:58.030367-05
10477	olga@gmail.com	page_visit	mobile_home	\N	\N	127.0.0.1	2025-06-24 07:13:28.489722-05
10478	olga@gmail.com	page_visit	mobile_my_team	\N	\N	127.0.0.1	2025-06-24 07:13:31.765353-05
10479	olga@gmail.com	page_visit	mobile_my_series	\N	\N	127.0.0.1	2025-06-24 07:13:35.602689-05
10480	olga@gmail.com	page_visit	mobile_my_club	\N	\N	127.0.0.1	2025-06-24 07:13:38.755952-05
10481	olga@gmail.com	page_visit	mobile_schedule_lesson	\N	\N	127.0.0.1	2025-06-24 07:14:12.851313-05
10482	olga@gmail.com	page_visit	track_byes_courts	\N	\N	127.0.0.1	2025-06-24 07:16:34.110357-05
10483	olga@gmail.com	page_visit	mobile_polls	\N	\N	127.0.0.1	2025-06-24 07:16:39.270914-05
10484	olga@gmail.com	page_visit	mobile_schedule_lesson	\N	\N	127.0.0.1	2025-06-24 07:17:41.207428-05
10485	olga@gmail.com	page_visit	mobile_schedule_lesson	\N	\N	127.0.0.1	2025-06-24 07:21:39.786533-05
10486	olga@gmail.com	page_visit	mobile_schedule_lesson	\N	\N	127.0.0.1	2025-06-24 07:21:47.020951-05
10487	olga@gmail.com	page_visit	mobile_home	\N	\N	127.0.0.1	2025-06-24 07:21:52.584663-05
10488	olga@gmail.com	page_visit	mobile_settings	\N	\N	127.0.0.1	2025-06-24 07:21:55.516272-05
10489	olga@gmail.com	page_visit	mobile_home	\N	\N	127.0.0.1	2025-06-24 07:22:00.713189-05
10490	olga@gmail.com	page_visit	mobile_find_people_to_play	\N	\N	127.0.0.1	2025-06-24 07:22:02.450075-05
10491	olga@gmail.com	page_visit	mobile_pickup_games	\N	\N	127.0.0.1	2025-06-24 07:22:11.286576-05
10492	olga@gmail.com	page_visit	mobile_schedule_lesson	\N	\N	127.0.0.1	2025-06-24 07:22:16.378822-05
10493	olga@gmail.com	page_visit	mobile_home	\N	\N	127.0.0.1	2025-06-24 07:24:37.765228-05
10494	olga@gmail.com	page_visit	mobile_find_people_to_play	\N	\N	127.0.0.1	2025-06-24 07:24:43.86466-05
10495	olga@gmail.com	page_visit	mobile_settings	\N	\N	127.0.0.1	2025-06-24 07:24:57.706823-05
10496	olga@gmail.com	page_visit	mobile_home	\N	\N	127.0.0.1	2025-06-24 07:25:22.114351-05
10497	olga@gmail.com	page_visit	mobile_schedule_lesson	\N	\N	127.0.0.1	2025-06-24 07:26:01.88258-05
10498	olga@gmail.com	page_visit	mobile_home	\N	\N	127.0.0.1	2025-06-24 07:28:33.022772-05
10499	olga@gmail.com	page_visit	mobile_find_people_to_play	\N	\N	127.0.0.1	2025-06-24 07:28:35.221065-05
10500	olga@gmail.com	page_visit	mobile_teams_players	\N	\N	127.0.0.1	2025-06-24 07:29:40.620961-05
10501	olga@gmail.com	page_visit	mobile_teams_players	\N	\N	127.0.0.1	2025-06-24 07:29:43.108247-05
10502	olga@gmail.com	page_visit	mobile_teams_players	\N	\N	127.0.0.1	2025-06-24 07:30:00.398999-05
10503	olga@gmail.com	page_visit	mobile_player_detail	\N	Viewed player Olga Martinsone	127.0.0.1	2025-06-24 07:30:11.44307-05
10504	olga@gmail.com	page_visit	mobile_player_detail	\N	Viewed player Olga Martinsone	127.0.0.1	2025-06-24 07:30:11.48471-05
10505	olga@gmail.com	page_visit	mobile_home	\N	\N	127.0.0.1	2025-06-24 07:30:20.694132-05
10506	olga@gmail.com	page_visit	mobile_find_people_to_play	\N	\N	127.0.0.1	2025-06-24 07:30:23.38647-05
10507	olga@gmail.com	page_visit	mobile_schedule_lesson	\N	\N	127.0.0.1	2025-06-24 07:33:46.764639-05
10508	olga@gmail.com	page_visit	mobile_schedule_lesson	\N	\N	127.0.0.1	2025-06-24 07:35:21.465193-05
10509	olga@gmail.com	page_visit	mobile_schedule_lesson	\N	\N	127.0.0.1	2025-06-24 07:36:04.890708-05
10510	olga@gmail.com	page_visit	mobile_schedule_lesson	\N	\N	127.0.0.1	2025-06-24 07:36:25.63209-05
10511	olga@gmail.com	page_visit	mobile_schedule_lesson	\N	\N	127.0.0.1	2025-06-24 07:36:26.481706-05
10512	olga@gmail.com	page_visit	mobile_schedule_lesson	\N	\N	127.0.0.1	2025-06-24 07:36:35.342815-05
10513	olga@gmail.com	page_visit	mobile_schedule_lesson	\N	\N	127.0.0.1	2025-06-24 07:36:44.14221-05
10514	olga@gmail.com	page_visit	mobile_home	\N	\N	127.0.0.1	2025-06-24 07:37:26.644377-05
10515	olga@gmail.com	page_visit	mobile_schedule_lesson	\N	\N	127.0.0.1	2025-06-24 07:37:30.578471-05
10516	olga@gmail.com	page_visit	mobile_home	\N	\N	127.0.0.1	2025-06-24 07:38:16.371627-05
10517	olga@gmail.com	page_visit	mobile_schedule_lesson	\N	\N	127.0.0.1	2025-06-24 07:38:46.055475-05
10518	olga@gmail.com	page_visit	mobile_player_search	\N	\N	127.0.0.1	2025-06-24 07:39:02.625922-05
10519	olga@gmail.com	page_visit	mobile_teams_players	\N	\N	127.0.0.1	2025-06-24 07:39:10.376819-05
10520	olga@gmail.com	page_visit	mobile_schedule_lesson	\N	\N	127.0.0.1	2025-06-24 07:39:16.244888-05
10521	olga@gmail.com	page_visit	mobile_home	\N	\N	127.0.0.1	2025-06-24 07:40:16.776853-05
10522	olga@gmail.com	page_visit	mobile_find_people_to_play	\N	\N	127.0.0.1	2025-06-24 07:40:19.008073-05
10523	olga@gmail.com	page_visit	mobile_pickup_games	\N	\N	127.0.0.1	2025-06-24 07:40:45.642566-05
10524	olga@gmail.com	page_visit	mobile_schedule_lesson	\N	\N	127.0.0.1	2025-06-24 07:44:13.911577-05
10525	olga@gmail.com	page_visit	mobile_schedule_lesson	\N	\N	127.0.0.1	2025-06-24 07:44:24.33451-05
10526	olga@gmail.com	page_visit	mobile_home	\N	\N	127.0.0.1	2025-06-24 07:44:49.392204-05
10527	olga@gmail.com	page_visit	mobile_teams_players	\N	\N	127.0.0.1	2025-06-24 07:46:01.632683-05
10528	olga@gmail.com	page_visit	mobile_home	\N	\N	127.0.0.1	2025-06-24 07:46:02.734964-05
10529	olga@gmail.com	page_visit	mobile_schedule_lesson	\N	\N	127.0.0.1	2025-06-24 07:46:11.200775-05
10530	olga@gmail.com	page_visit	mobile_schedule_lesson	\N	\N	127.0.0.1	2025-06-24 07:46:21.690078-05
10531	olga@gmail.com	page_visit	mobile_home	\N	\N	127.0.0.1	2025-06-24 07:46:55.918023-05
10532	olga@gmail.com	page_visit	mobile_schedule_lesson	\N	\N	127.0.0.1	2025-06-24 07:49:10.741743-05
10533	olga@gmail.com	page_visit	mobile_home	\N	\N	127.0.0.1	2025-06-24 07:49:22.766868-05
10534	olga@gmail.com	page_visit	mobile_find_people_to_play	\N	\N	127.0.0.1	2025-06-24 07:49:42.11387-05
10535	olga@gmail.com	page_visit	mobile_home	\N	\N	127.0.0.1	2025-06-24 07:49:44.741424-05
10536	olga@gmail.com	page_visit	mobile_player_search	\N	\N	127.0.0.1	2025-06-24 07:49:48.06111-05
10537	olga@gmail.com	page_visit	mobile_player_search	\N	\N	127.0.0.1	2025-06-24 07:49:49.231127-05
10538	olga@gmail.com	player_search	\N	\N	Searched for first name "rr", found 33 matches	127.0.0.1	2025-06-24 07:49:52.530806-05
10539	olga@gmail.com	page_visit	mobile_player_search	\N	\N	127.0.0.1	2025-06-24 07:49:52.533312-05
10540	olga@gmail.com	page_visit	mobile_home	\N	\N	127.0.0.1	2025-06-24 07:49:54.557922-05
10541	olga@gmail.com	page_visit	mobile_matchup_simulator	\N	\N	127.0.0.1	2025-06-24 07:50:05.479625-05
10542	olga@gmail.com	page_visit	mobile_settings	\N	\N	127.0.0.1	2025-06-24 07:50:24.051511-05
10543	olga@gmail.com	page_visit	mobile_home	\N	\N	127.0.0.1	2025-06-24 07:50:31.586301-05
10544	olga@gmail.com	page_visit	mobile_matchup_simulator	\N	\N	127.0.0.1	2025-06-24 07:50:38.753644-05
10545	olga@gmail.com	page_visit	mobile_home	\N	\N	127.0.0.1	2025-06-24 07:51:12.806488-05
10546	olga@gmail.com	page_visit	mobile_schedule_lesson	\N	\N	127.0.0.1	2025-06-24 07:51:17.391704-05
10547	olga@gmail.com	page_visit	mobile_schedule_lesson	\N	\N	127.0.0.1	2025-06-24 09:24:03.698612-05
10548	olga@gmail.com	page_visit	mobile_schedule_lesson	\N	\N	127.0.0.1	2025-06-24 09:24:04.242606-05
10549	olga@gmail.com	page_visit	mobile_home	\N	\N	127.0.0.1	2025-06-24 09:24:43.183095-05
10550	olga@gmail.com	page_visit	mobile_matchup_simulator	\N	\N	127.0.0.1	2025-06-24 09:24:45.830316-05
10551	olga@gmail.com	simulation_run	mobile_matchup_simulator	\N	Team A: Joann Williams & Katie Ramoley vs Team B: Erica Zipp & Angela Riedel	127.0.0.1	2025-06-24 09:25:00.311566-05
10552	olga@gmail.com	page_visit	track_byes_courts	\N	\N	127.0.0.1	2025-06-24 09:33:07.74213-05
10553	olga@gmail.com	page_visit	mobile_find_people_to_play	\N	\N	127.0.0.1	2025-06-24 09:33:16.701046-05
10554	olga@gmail.com	page_visit	mobile_pickup_games	\N	\N	127.0.0.1	2025-06-24 09:33:25.794921-05
10555	olga@gmail.com	page_visit	mobile_pickup_games	\N	\N	127.0.0.1	2025-06-24 09:33:34.456224-05
10556	olga@gmail.com	page_visit	mobile_home	\N	\N	127.0.0.1	2025-06-24 09:37:32.040073-05
10557	olga@gmail.com	page_visit	mobile_schedule_lesson	\N	\N	127.0.0.1	2025-06-24 09:37:34.742825-05
10558	olga@gmail.com	page_visit	mobile_player_search	\N	\N	127.0.0.1	2025-06-24 09:38:45.376781-05
10559	olga@gmail.com	player_search	\N	\N	Searched for last name "israel", found 1 matches	127.0.0.1	2025-06-24 09:38:54.793795-05
10560	olga@gmail.com	page_visit	mobile_player_search	\N	\N	127.0.0.1	2025-06-24 09:38:54.800561-05
10561	olga@gmail.com	page_visit	mobile_player_detail	\N	Viewed player Amy Israel	127.0.0.1	2025-06-24 09:38:57.258004-05
10562	olga@gmail.com	page_visit	mobile_home	\N	\N	127.0.0.1	2025-06-24 09:39:06.203557-05
10563	olga@gmail.com	page_visit	mobile_settings	\N	\N	127.0.0.1	2025-06-24 09:39:09.221853-05
10564	vforman@gmail.com	auth	\N	login	Login successful. 1 associated players	127.0.0.1	2025-06-24 09:39:19.095591-05
10565	vforman@gmail.com	page_visit	mobile_home	\N	\N	127.0.0.1	2025-06-24 09:39:19.119284-05
10566	vforman@gmail.com	page_visit	mobile_settings	\N	\N	127.0.0.1	2025-06-24 09:39:21.708562-05
10567	vforman@gmail.com	page_visit	mobile_settings	\N	\N	127.0.0.1	2025-06-24 09:39:26.811622-05
10568	vforman@gmail.com	page_visit	mobile_home	\N	\N	127.0.0.1	2025-06-24 09:39:27.466097-05
10569	vforman@gmail.com	page_visit	track_byes_courts	\N	\N	127.0.0.1	2025-06-24 09:39:30.457876-05
10570	vforman@gmail.com	page_visit	mobile_home	\N	\N	127.0.0.1	2025-06-24 09:39:36.861897-05
10571	vforman@gmail.com	page_visit	mobile_pickup_games	\N	\N	127.0.0.1	2025-06-24 09:39:39.285812-05
10572	vforman@gmail.com	page_visit	mobile_pickup_games	\N	\N	127.0.0.1	2025-06-24 09:40:05.486295-05
10573	vforman@gmail.com	page_visit	mobile_pickup_games	\N	\N	127.0.0.1	2025-06-24 09:40:14.205634-05
10574	vforman@gmail.com	page_visit	mobile_pickup_games	\N	\N	127.0.0.1	2025-06-24 09:40:36.05101-05
10575	vforman@gmail.com	page_visit	mobile_home	\N	\N	127.0.0.1	2025-06-24 09:40:53.388002-05
10576	vforman@gmail.com	page_visit	mobile_schedule_lesson	\N	\N	127.0.0.1	2025-06-24 09:40:56.092251-05
10577	vforman@gmail.com	page_visit	mobile_home	\N	\N	127.0.0.1	2025-06-24 09:41:46.686382-05
10578	vforman@gmail.com	page_visit	mobile_pickup_games	\N	\N	127.0.0.1	2025-06-24 09:41:56.725198-05
10579	vforman@gmail.com	page_visit	mobile_home	\N	\N	127.0.0.1	2025-06-24 09:42:35.499422-05
10580	vforman@gmail.com	page_visit	mobile_home	\N	\N	127.0.0.1	2025-06-24 09:42:35.772811-05
10581	vforman@gmail.com	page_visit	mobile_pickup_games	\N	\N	127.0.0.1	2025-06-24 09:42:55.917017-05
10582	vforman@gmail.com	page_visit	mobile_pickup_games	\N	\N	127.0.0.1	2025-06-24 09:44:31.170741-05
10583	vforman@gmail.com	page_visit	mobile_home	\N	\N	127.0.0.1	2025-06-24 09:44:37.892655-05
10584	vforman@gmail.com	page_visit	mobile_schedule_lesson	\N	\N	127.0.0.1	2025-06-24 09:44:41.27611-05
10585	vforman@gmail.com	page_visit	mobile_home	\N	\N	127.0.0.1	2025-06-24 09:45:29.506256-05
10586	vforman@gmail.com	page_visit	mobile_pickup_games	\N	\N	127.0.0.1	2025-06-24 09:45:31.548233-05
10587	vforman@gmail.com	page_visit	mobile_home	\N	\N	127.0.0.1	2025-06-24 09:46:10.937258-05
10588	vforman@gmail.com	page_visit	mobile_schedule_lesson	\N	\N	127.0.0.1	2025-06-24 09:46:13.912689-05
10589	vforman@gmail.com	page_visit	mobile_schedule_lesson	\N	\N	127.0.0.1	2025-06-24 09:47:23.052571-05
10590	vforman@gmail.com	page_visit	mobile_schedule_lesson	\N	\N	127.0.0.1	2025-06-24 09:47:24.70897-05
10591	vforman@gmail.com	page_visit	mobile_schedule_lesson	\N	\N	127.0.0.1	2025-06-24 09:48:15.964593-05
10592	vforman@gmail.com	page_visit	mobile_home	\N	\N	127.0.0.1	2025-06-24 09:48:28.528562-05
10593	vforman@gmail.com	page_visit	mobile_schedule_lesson	\N	\N	127.0.0.1	2025-06-24 09:48:31.384973-05
10594	vforman@gmail.com	page_visit	mobile_schedule_lesson	\N	\N	127.0.0.1	2025-06-24 09:48:40.681667-05
10595	vforman@gmail.com	page_visit	mobile_home	\N	\N	127.0.0.1	2025-06-24 09:48:48.676008-05
10596	vforman@gmail.com	page_visit	mobile_pickup_games	\N	\N	127.0.0.1	2025-06-24 09:48:53.065579-05
10597	vforman@gmail.com	page_visit	mobile_schedule_lesson	\N	\N	127.0.0.1	2025-06-24 09:50:44.053755-05
10598	vforman@gmail.com	page_visit	mobile_home	\N	\N	127.0.0.1	2025-06-24 09:51:57.875289-05
10599	vforman@gmail.com	page_visit	mobile_find_subs	\N	\N	127.0.0.1	2025-06-24 09:52:03.256849-05
10600	vforman@gmail.com	page_visit	mobile_home	\N	\N	127.0.0.1	2025-06-24 09:52:05.944805-05
10601	vforman@gmail.com	page_visit	mobile_my_club	\N	\N	127.0.0.1	2025-06-24 09:52:24.525929-05
10602	vforman@gmail.com	page_visit	mobile_team_schedule	\N	\N	127.0.0.1	2025-06-24 09:52:30.449332-05
10603	vforman@gmail.com	page_visit	mobile_home	\N	\N	127.0.0.1	2025-06-24 09:53:16.330536-05
10604	vforman@gmail.com	page_visit	mobile_pickup_games	\N	\N	127.0.0.1	2025-06-24 09:53:19.172098-05
10605	rossfreedman@gmail.com	auth	\N	login	Login successful. 2 associated players	127.0.0.1	2025-06-24 09:55:06.975122-05
10606	rossfreedman@gmail.com	page_visit	mobile_team_schedule	\N	\N	127.0.0.1	2025-06-24 09:55:06.99088-05
10607	vforman@gmail.com	page_visit	mobile_home	\N	\N	127.0.0.1	2025-06-24 09:55:58.278511-05
10608	vforman@gmail.com	page_visit	mobile_team_schedule	\N	\N	127.0.0.1	2025-06-24 09:56:01.933038-05
10609	vforman@gmail.com	page_visit	mobile_home	\N	\N	127.0.0.1	2025-06-24 09:56:17.265053-05
10610	vforman@gmail.com	page_visit	mobile_availability_calendar	\N	\N	127.0.0.1	2025-06-24 09:56:22.222647-05
10611	vforman@gmail.com	availability_update	\N	availability_update	Set availability for 2024-09-24 to status 2 (Player: Victor Forman, ID: nndz-WkMrK3diZjZoZz09)	127.0.0.1	2025-06-24 09:56:26.410211-05
10612	vforman@gmail.com	availability_update	\N	availability_update	Set availability for 2024-09-24 to status 2 (Player: Victor Forman, ID: nndz-WkMrK3diZjZoZz09)	127.0.0.1	2025-06-24 09:56:32.508325-05
10613	vforman@gmail.com	page_visit	mobile_home	\N	\N	127.0.0.1	2025-06-24 09:56:34.536663-05
10614	vforman@gmail.com	page_visit	mobile_team_schedule	\N	\N	127.0.0.1	2025-06-24 09:56:36.816776-05
10615	vforman@gmail.com	page_visit	mobile_home	\N	\N	127.0.0.1	2025-06-24 09:56:48.880585-05
10616	vforman@gmail.com	page_visit	mobile_pickup_games	\N	\N	127.0.0.1	2025-06-24 09:56:50.285481-05
10617	vforman@gmail.com	page_visit	mobile_home	\N	\N	127.0.0.1	2025-06-24 09:58:51.322509-05
10618	vforman@gmail.com	page_visit	mobile_player_search	\N	\N	127.0.0.1	2025-06-24 09:59:48.91789-05
10619	vforman@gmail.com	player_search	\N	\N	Searched for first name "israel", found 0 matches	127.0.0.1	2025-06-24 09:59:52.650244-05
10620	vforman@gmail.com	page_visit	mobile_player_search	\N	\N	127.0.0.1	2025-06-24 09:59:52.655978-05
10621	vforman@gmail.com	page_visit	mobile_home	\N	\N	127.0.0.1	2025-06-24 09:59:54.517526-05
10622	vforman@gmail.com	page_visit	mobile_player_search	\N	\N	127.0.0.1	2025-06-24 09:59:57.678863-05
10623	vforman@gmail.com	player_search	\N	\N	Searched for last name "israel", found 2 matches	127.0.0.1	2025-06-24 10:00:02.003085-05
10624	vforman@gmail.com	page_visit	mobile_player_search	\N	\N	127.0.0.1	2025-06-24 10:00:02.009868-05
10625	vforman@gmail.com	page_visit	mobile_player_detail	\N	Viewed player David Israel	127.0.0.1	2025-06-24 10:00:04.002062-05
10626	vforman@gmail.com	page_visit	mobile_teams_players	\N	\N	127.0.0.1	2025-06-24 10:00:14.913565-05
10627	vforman@gmail.com	page_visit	mobile_teams_players	\N	\N	127.0.0.1	2025-06-24 10:00:19.080183-05
10628	vforman@gmail.com	page_visit	mobile_home	\N	\N	127.0.0.1	2025-06-24 10:00:27.243592-05
10629	vforman@gmail.com	page_visit	mobile_analyze_me	\N	\N	127.0.0.1	2025-06-24 10:00:32.244244-05
10630	vforman@gmail.com	page_visit	mobile_home	\N	\N	127.0.0.1	2025-06-24 10:00:34.803158-05
10631	vforman@gmail.com	page_visit	mobile_my_team	\N	\N	127.0.0.1	2025-06-24 10:00:37.225073-05
10632	vforman@gmail.com	page_visit	mobile_home	\N	\N	127.0.0.1	2025-06-24 10:01:35.678029-05
10633	vforman@gmail.com	page_visit	mobile_pickup_games	\N	\N	127.0.0.1	2025-06-24 10:01:37.336236-05
10634	vforman@gmail.com	page_visit	mobile_home	\N	\N	127.0.0.1	2025-06-24 10:02:59.330353-05
10635	vforman@gmail.com	page_visit	mobile_analyze_me	\N	\N	127.0.0.1	2025-06-24 10:03:01.422787-05
10636	vforman@gmail.com	page_visit	mobile_home	\N	\N	127.0.0.1	2025-06-24 10:03:03.151455-05
10637	vforman@gmail.com	page_visit	mobile_my_team	\N	\N	127.0.0.1	2025-06-24 10:03:05.373624-05
10638	vforman@gmail.com	page_visit	mobile_home	\N	\N	127.0.0.1	2025-06-24 10:03:30.977125-05
10639	vforman@gmail.com	page_visit	mobile_pickup_games	\N	\N	127.0.0.1	2025-06-24 10:03:32.682365-05
10640	vforman@gmail.com	page_visit	mobile_pickup_games	\N	\N	127.0.0.1	2025-06-24 10:04:26.77911-05
10641	vforman@gmail.com	page_visit	mobile_home	\N	\N	127.0.0.1	2025-06-24 10:04:42.312014-05
10642	vforman@gmail.com	page_visit	mobile_availability	\N	\N	127.0.0.1	2025-06-24 10:04:43.923631-05
10643	vforman@gmail.com	page_visit	mobile_home	\N	\N	127.0.0.1	2025-06-24 10:04:56.978299-05
10644	vforman@gmail.com	page_visit	mobile_schedule_lesson	\N	\N	127.0.0.1	2025-06-24 10:05:00.755568-05
10645	vforman@gmail.com	page_visit	mobile_home	\N	\N	127.0.0.1	2025-06-24 10:05:09.305458-05
10646	vforman@gmail.com	page_visit	mobile_pickup_games	\N	\N	127.0.0.1	2025-06-24 10:05:22.057748-05
10647	vforman@gmail.com	page_visit	mobile_create_pickup_game	\N	\N	127.0.0.1	2025-06-24 10:05:25.240914-05
10648	rossfreedman@gmail.com	auth	\N	login	Login successful. 2 associated players	73.22.198.26	2025-06-24 10:32:42.647137-05
10649	rossfreedman@gmail.com	page_visit	mobile_home	\N	\N	73.22.198.26	2025-06-24 10:32:42.785167-05
10650	rossfreedman@gmail.com	page_visit	mobile_improve	\N	Accessed improve page	73.22.198.26	2025-06-24 10:32:44.559872-05
10651	rossfreedman@gmail.com	page_visit	mobile_home	\N	\N	73.22.198.26	2025-06-24 10:32:47.855511-05
10652	rossfreedman@gmail.com	page_visit	mobile_availability	\N	\N	73.22.198.26	2025-06-24 10:32:50.949147-05
10653	rossfreedman@gmail.com	page_visit	mobile_home	\N	\N	73.22.198.26	2025-06-24 10:32:58.341769-05
10654	rossfreedman@gmail.com	page_visit	mobile_analyze_me	\N	\N	73.22.198.26	2025-06-24 10:33:01.070527-05
10655	rossfreedman@gmail.com	page_visit	mobile_home	\N	\N	73.22.198.26	2025-06-24 10:33:05.17974-05
10656	rossfreedman@gmail.com	page_visit	track_byes_courts	\N	\N	73.22.198.26	2025-06-24 10:33:36.93626-05
10657	rossfreedman@gmail.com	page_visit	mobile_home	\N	\N	73.22.198.26	2025-06-24 10:35:39.296917-05
10658	rossfreedman@gmail.com	page_visit	mobile_home	\N	\N	127.0.0.1	2025-06-24 11:12:54.583318-05
10659	rossfreedman@gmail.com	page_visit	mobile_availability	\N	\N	127.0.0.1	2025-06-24 11:12:56.329082-05
10660	rossfreedman@gmail.com	page_visit	mobile_find_people_to_play	\N	\N	127.0.0.1	2025-06-24 11:12:58.640919-05
10661	rossfreedman@gmail.com	page_visit	mobile_home	\N	\N	127.0.0.1	2025-06-24 11:13:05.503493-05
10662	rossfreedman@gmail.com	page_visit	mobile_analyze_me	\N	\N	127.0.0.1	2025-06-24 11:13:13.621043-05
10663	rossfreedman@gmail.com	page_visit	mobile_home	\N	\N	127.0.0.1	2025-06-24 11:13:19.163586-05
10664	rossfreedman@gmail.com	page_visit	mobile_my_team	\N	\N	127.0.0.1	2025-06-24 11:13:21.706239-05
10665	rossfreedman@gmail.com	page_visit	mobile_home	\N	\N	127.0.0.1	2025-06-24 11:13:23.031599-05
10666	rossfreedman@gmail.com	page_visit	mobile_my_club	\N	\N	127.0.0.1	2025-06-24 11:13:27.490244-05
10667	rossfreedman@gmail.com	page_visit	mobile_home	\N	\N	127.0.0.1	2025-06-24 11:13:28.186478-05
10668	rossfreedman@gmail.com	page_visit	mobile_team_schedule	\N	\N	127.0.0.1	2025-06-24 11:13:32.89109-05
10669	rossfreedman@gmail.com	page_visit	mobile_home	\N	\N	127.0.0.1	2025-06-24 13:52:07.095265-05
10670	rossfreedman@gmail.com	page_visit	mobile_my_club	\N	\N	127.0.0.1	2025-06-24 13:52:18.955723-05
10671	rossfreedman@gmail.com	page_visit	mobile_home	\N	\N	127.0.0.1	2025-06-24 14:01:02.811275-05
10672	rossfreedman@gmail.com	page_visit	mobile_settings	\N	\N	127.0.0.1	2025-06-24 15:39:42.319063-05
10758	vforman@gmail.com	page_visit	mobile_home	\N	\N	127.0.0.1	2025-06-24 19:43:28.083317-05
10759	vforman@gmail.com	page_visit	mobile_analyze_me	\N	\N	127.0.0.1	2025-06-24 19:45:03.969279-05
10760	vforman@gmail.com	page_visit	mobile_my_team	\N	\N	127.0.0.1	2025-06-24 19:45:07.341303-05
10761	vforman@gmail.com	page_visit	mobile_settings	\N	\N	127.0.0.1	2025-06-24 19:45:12.535152-05
10762	vforman@gmail.com	auth	\N	login	Login successful. 0 associated players	127.0.0.1	2025-06-24 19:45:22.095366-05
10763	vforman@gmail.com	page_visit	mobile_home	\N	\N	127.0.0.1	2025-06-24 19:45:22.121094-05
10764	vforman@gmail.com	page_visit	mobile_settings	\N	\N	127.0.0.1	2025-06-24 19:45:29.564641-05
10765	vforman@gmail.com	page_visit	mobile_home	\N	\N	127.0.0.1	2025-06-24 19:45:37.537753-05
10683	rossfreedman@gmail.com	auth	\N	login	Login successful. 2 associated players	127.0.0.1	2025-06-24 15:53:17.571843-05
10684	rossfreedman@gmail.com	page_visit	mobile_home	\N	\N	127.0.0.1	2025-06-24 15:53:17.598126-05
10685	rossfreedman@gmail.com	page_visit	admin	\N	\N	127.0.0.1	2025-06-24 15:53:19.728639-05
10686	rossfreedman@gmail.com	page_visit	admin_users	\N	\N	127.0.0.1	2025-06-24 15:53:20.945573-05
10687	rossfreedman@gmail.com	admin_action	\N	delete_user	Deleted user: Patrick Katai (patrick.katai.complete@example.com)	127.0.0.1	2025-06-24 15:53:27.854814-05
10688	rossfreedman@gmail.com	admin_action	\N	delete_user	Deleted user: Pete Katai (pete.katai.test@example.com)	127.0.0.1	2025-06-24 15:53:31.939418-05
10689	rossfreedman@gmail.com	admin_action	\N	delete_user	Deleted user: Peter Katai (pkatai@gmail.com)	127.0.0.1	2025-06-24 15:53:34.418708-05
10690	rossfreedman@gmail.com	page_visit	mobile_home	\N	\N	127.0.0.1	2025-06-24 15:53:40.126897-05
10691	rossfreedman@gmail.com	page_visit	mobile_settings	\N	\N	127.0.0.1	2025-06-24 15:53:41.528441-05
10692	pkatai@gmail.com	auth	\N	register	Registration successful. Player association created with exact match and team assignment verified	127.0.0.1	2025-06-24 15:54:02.787179-05
10693	pkatai@gmail.com	page_visit	mobile_home	\N	\N	127.0.0.1	2025-06-24 15:54:02.811864-05
10694	pkatai@gmail.com	page_visit	mobile_home	\N	\N	127.0.0.1	2025-06-24 16:43:52.913986-05
10695	pkatai@gmail.com	page_visit	mobile_my_club	\N	\N	127.0.0.1	2025-06-24 16:45:03.966862-05
10696	pkatai@gmail.com	page_visit	mobile_settings	\N	\N	127.0.0.1	2025-06-24 16:46:57.776242-05
10697	pkatai@gmail.com	page_visit	mobile_home	\N	\N	127.0.0.1	2025-06-24 16:51:49.268805-05
10698	pkatai@gmail.com	page_visit	mobile_my_club	\N	\N	127.0.0.1	2025-06-24 16:51:55.689589-05
10699	pkatai@gmail.com	page_visit	mobile_settings	\N	\N	127.0.0.1	2025-06-24 16:55:32.26847-05
10700	pkatai@gmail.com	page_visit	mobile_home	\N	\N	127.0.0.1	2025-06-24 16:55:35.385519-05
10701	pkatai@gmail.com	page_visit	mobile_my_club	\N	\N	127.0.0.1	2025-06-24 16:55:42.785227-05
10702	pkatai@gmail.com	page_visit	mobile_settings	\N	\N	127.0.0.1	2025-06-24 16:57:22.012275-05
10703	pkatai@gmail.com	page_visit	mobile_home	\N	\N	127.0.0.1	2025-06-24 16:57:29.686529-05
10704	pkatai@gmail.com	page_visit	mobile_analyze_me	\N	\N	127.0.0.1	2025-06-24 17:00:50.024593-05
10705	pkatai@gmail.com	page_visit	mobile_home	\N	\N	127.0.0.1	2025-06-24 17:01:45.180516-05
10706	pkatai@gmail.com	page_visit	mobile_my_club	\N	\N	127.0.0.1	2025-06-24 17:01:49.652533-05
10707	pkatai@gmail.com	page_visit	mobile_home	\N	\N	127.0.0.1	2025-06-24 17:05:08.363462-05
10708	pkatai@gmail.com	page_visit	mobile_my_series	\N	\N	127.0.0.1	2025-06-24 17:05:11.297407-05
10709	pkatai@gmail.com	page_visit	mobile_home	\N	\N	127.0.0.1	2025-06-24 17:11:55.322916-05
10710	pkatai@gmail.com	page_visit	mobile_my_club	\N	\N	127.0.0.1	2025-06-24 17:11:59.790734-05
10711	pkatai@gmail.com	page_visit	mobile_home	\N	\N	127.0.0.1	2025-06-24 17:16:30.171076-05
10712	pkatai@gmail.com	page_visit	mobile_lineup_selection	\N	\N	127.0.0.1	2025-06-24 17:16:39.690541-05
10713	pkatai@gmail.com	page_visit	mobile_my_club	\N	\N	127.0.0.1	2025-06-24 17:19:15.875681-05
10714	pkatai@gmail.com	page_visit	mobile_home	\N	\N	127.0.0.1	2025-06-24 17:58:48.932644-05
10715	pkatai@gmail.com	page_visit	mobile_my_series	\N	\N	127.0.0.1	2025-06-24 17:58:57.696199-05
10716	pkatai@gmail.com	page_visit	mobile_home	\N	\N	127.0.0.1	2025-06-24 18:02:38.768927-05
10717	pkatai@gmail.com	page_visit	mobile_my_series	\N	\N	127.0.0.1	2025-06-24 18:02:46.411087-05
10718	pkatai@gmail.com	page_visit	mobile_my_series	\N	\N	127.0.0.1	2025-06-24 18:09:49.780653-05
10719	pkatai@gmail.com	page_visit	mobile_home	\N	\N	127.0.0.1	2025-06-24 18:10:12.249785-05
10720	pkatai@gmail.com	page_visit	mobile_settings	\N	\N	127.0.0.1	2025-06-24 18:10:14.220394-05
10721	rossfreedman@gmail.com	auth	\N	login	Login successful. 2 associated players	127.0.0.1	2025-06-24 18:10:29.057008-05
10722	rossfreedman@gmail.com	page_visit	mobile_home	\N	\N	127.0.0.1	2025-06-24 18:10:29.085953-05
10723	rossfreedman@gmail.com	page_visit	mobile_my_series	\N	\N	127.0.0.1	2025-06-24 18:10:33.8744-05
10724	rossfreedman@gmail.com	page_visit	mobile_my_series	\N	\N	127.0.0.1	2025-06-24 18:16:43.815652-05
10725	rossfreedman@gmail.com	page_visit	mobile_my_series	\N	\N	127.0.0.1	2025-06-24 18:21:41.126156-05
10726	rossfreedman@gmail.com	page_visit	mobile_home	\N	\N	127.0.0.1	2025-06-24 18:23:32.38853-05
10727	rossfreedman@gmail.com	page_visit	mobile_analyze_me	\N	\N	127.0.0.1	2025-06-24 18:23:35.804676-05
10728	rossfreedman@gmail.com	page_visit	mobile_home	\N	\N	127.0.0.1	2025-06-24 18:24:40.927297-05
10729	rossfreedman@gmail.com	page_visit	mobile_home	\N	\N	127.0.0.1	2025-06-24 18:24:41.162665-05
10730	rossfreedman@gmail.com	page_visit	mobile_settings	\N	\N	127.0.0.1	2025-06-24 18:26:09.245988-05
10731	vforman@gmail.com	auth	\N	login	Login successful. 1 associated players	127.0.0.1	2025-06-24 18:26:17.724139-05
10732	vforman@gmail.com	page_visit	mobile_home	\N	\N	127.0.0.1	2025-06-24 18:26:17.749836-05
10733	vforman@gmail.com	page_visit	mobile_analyze_me	\N	\N	127.0.0.1	2025-06-24 18:26:23.851143-05
10734	vforman@gmail.com	page_visit	mobile_home	\N	\N	127.0.0.1	2025-06-24 18:27:49.997279-05
10735	vforman@gmail.com	page_visit	mobile_analyze_me	\N	\N	127.0.0.1	2025-06-24 18:29:14.551397-05
10736	vforman@gmail.com	page_visit	mobile_analyze_me	\N	\N	127.0.0.1	2025-06-24 18:31:05.527768-05
10737	vforman@gmail.com	page_visit	mobile_home	\N	\N	127.0.0.1	2025-06-24 18:32:47.663194-05
10738	vforman@gmail.com	page_visit	mobile_settings	\N	\N	127.0.0.1	2025-06-24 18:32:49.276538-05
10739	vforman@gmail.com	page_visit	mobile_analyze_me	\N	\N	127.0.0.1	2025-06-24 18:33:43.582508-05
10740	vforman@gmail.com	page_visit	mobile_analyze_me	\N	\N	127.0.0.1	2025-06-24 18:35:01.323441-05
10741	vforman@gmail.com	page_visit	mobile_analyze_me	\N	\N	127.0.0.1	2025-06-24 18:36:09.861558-05
10742	vforman@gmail.com	page_visit	mobile_analyze_me	\N	\N	127.0.0.1	2025-06-24 18:39:37.551445-05
10743	vforman@gmail.com	page_visit	mobile_analyze_me	\N	\N	127.0.0.1	2025-06-24 18:40:00.581267-05
10744	vforman@gmail.com	page_visit	mobile_analyze_me	\N	\N	127.0.0.1	2025-06-24 18:40:22.887166-05
10745	vforman@gmail.com	page_visit	mobile_home	\N	\N	127.0.0.1	2025-06-24 18:40:35.803357-05
10746	vforman@gmail.com	page_visit	mobile_analyze_me	\N	\N	127.0.0.1	2025-06-24 18:40:58.783334-05
10747	vforman@gmail.com	page_visit	mobile_analyze_me	\N	\N	127.0.0.1	2025-06-24 18:42:52.377055-05
10748	vforman@gmail.com	page_visit	mobile_settings	\N	\N	127.0.0.1	2025-06-24 18:43:45.73523-05
10749	vforman@gmail.com	page_visit	mobile_home	\N	\N	127.0.0.1	2025-06-24 18:47:03.449052-05
10750	vforman@gmail.com	page_visit	mobile_analyze_me	\N	\N	127.0.0.1	2025-06-24 18:47:07.953153-05
10751	vforman@gmail.com	page_visit	mobile_analyze_me	\N	\N	127.0.0.1	2025-06-24 18:58:42.588684-05
10752	vforman@gmail.com	page_visit	mobile_analyze_me	\N	\N	127.0.0.1	2025-06-24 19:27:43.924813-05
10753	vforman@gmail.com	page_visit	mobile_home	\N	\N	127.0.0.1	2025-06-24 19:42:51.208991-05
10754	vforman@gmail.com	page_visit	mobile_my_team	\N	\N	127.0.0.1	2025-06-24 19:42:53.818989-05
10755	vforman@gmail.com	page_visit	mobile_my_team	\N	\N	127.0.0.1	2025-06-24 19:43:03.782223-05
10756	vforman@gmail.com	page_visit	mobile_my_team	\N	\N	127.0.0.1	2025-06-24 19:43:23.842822-05
10757	vforman@gmail.com	page_visit	mobile_my_team	\N	\N	127.0.0.1	2025-06-24 19:43:26.22258-05
\.


--
-- TOC entry 4176 (class 0 OID 46627)
-- Dependencies: 262
-- Data for Name: user_instructions; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.user_instructions (id, user_email, instruction, series_id, team_id, created_at, is_active) FROM stdin;
\.


--
-- TOC entry 4142 (class 0 OID 46494)
-- Dependencies: 227
-- Data for Name: user_player_associations; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.user_player_associations (user_id, is_primary, created_at, tenniscores_player_id) FROM stdin;
70	t	2025-06-18 14:38:07.837213-05	nndz-WkM2L3hMcjloQT09
72	t	2025-06-18 19:29:20.268252-05	nndz-WlNlN3dyYnhqUT09
73	t	2025-06-20 08:11:49.061616-05	nndz-WkMrK3dyejhodz09
74	t	2025-06-20 08:40:55.228084-05	nndz-WkM2L3c3bjlqUT09
76	t	2025-06-20 16:03:21.313314-05	nndz-WkM2eHhybi9qUT09
77	t	2025-06-21 12:43:42.446194-05	nndz-WkMrK3dMMzdndz09
50	t	2025-06-14 08:14:11.368702-05	nndz-WkNDNnhyYjZoZz09
51	t	2025-06-14 16:23:26.977497-05	nndz-WkM2L3c3djZnQT09
49	t	2025-06-15 21:04:39.113155-05	nndz-WkMrK3diZjZoZz09
52	t	2025-06-16 07:54:06.764607-05	nndz-WkNPd3g3Yjlndz09
79	t	2025-06-22 06:56:46.56616-05	nndz-WkM2eHhybndoZz09
161	t	2025-06-22 13:05:47.164307-05	nndz-WkNPd3g3citnQT09
349	t	2025-06-23 16:00:49.844705-05	nndz-WkM2L3c3bjhoUT09
350	f	2025-06-23 16:47:44.612545-05	nndz-WlNld3g3bnhoQT09
350	t	2025-06-23 16:47:23.157448-05	nndz-WkNHeHdiZjVoUT09
43	f	2025-06-19 15:39:37.137969-05	nndz-WlNhd3hMYi9nQT09
43	t	2025-06-13 20:09:14.756713-05	nndz-WkMrK3didjlnUT09
352	t	2025-06-23 21:30:47.038437-05	nndz-WkNDd3liZitqQT09
356	t	2025-06-23 21:38:51.882322-05	nndz-WkNPd3liNzlnQT09
357	t	2025-06-23 21:40:57.633481-05	nndz-WkNPd3liNzlnQT09
399	t	2025-06-23 22:01:16.941956-05	nndz-WkNPd3liNzlnQT09
403	t	2025-06-23 22:32:07.056969-05	nndz-WkNPd3hydjdqUT09
404	t	2025-06-24 07:10:37.532588-05	nndz-WkM2eHhidi9qUT09
409	t	2025-06-24 15:54:02.759624-05	nndz-WkNDd3liZnhoQT09
\.


--
-- TOC entry 4143 (class 0 OID 46499)
-- Dependencies: 228
-- Data for Name: users; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.users (id, email, password_hash, first_name, last_name, club_automation_password, created_at, last_login, is_admin, ad_deuce_preference, dominant_hand, league_id, tenniscores_player_id) FROM stdin;
73	aguon@gmail.com	pbkdf2:sha256:1000000$ZB2RSeR38lYYgiHq$04b20ce8ce5705622a002dad6b9638bec64b9062861e105fca7ea1b697cfa2ca	Allen	Guon	\N	2025-06-20 08:11:49.061616-05	\N	f	\N	\N	4501	\N
51	sstatkus@gmail.com	pbkdf2:sha256:1000000$Io8GqcMFvB5EfAqL$97b3898ea191f64330807c99202d7094e25badd770c8e43e23c721eafcfce46c	Stephen	Statkus		2025-06-14 16:23:26.977497-05	\N	f	\N	\N	4501	\N
50	aseyb@gmail.com	pbkdf2:sha256:1000000$I03ZbogiUZ2DmDiJ$405787e2cb3c3f99f757319d7f80f09d2990d4c3032b21868b7ea6a9dfc6635d	Adam	Seyb	\N	2025-06-14 08:14:11.368702-05	2025-06-15 21:08:01.733426-05	f	\N	\N	4501	\N
52	mborchew@gmail.com	pbkdf2:sha256:1000000$otbbJzVRpzDBjfCP$b39549e95f8b9e7e5e8beb6b25fb2c5057a2651e99f967d87975b066db3b29d6	Mike	Borchew		2025-06-16 07:54:06.764607-05	\N	f	\N	\N	4501	\N
74	bstutland@gmail.com	pbkdf2:sha256:1000000$o0kkGb9Rn2A2knMj$c8644602e87a40e18f5ec897f7ead8280e69c5f9b24c30980db226d60775fb1e	Brian	Stutland	\N	2025-06-20 08:40:55.228084-05	2025-06-20 10:06:01.825589-05	f	\N	\N	4501	\N
70	disrael@gmail.com	pbkdf2:sha256:1000000$zvkJWtuzng8NAN2N$afd50bf968b58f49c6a8910a83ec3103f501c275f97fc7fd23cc5164994350ce	Dave	Israel		2025-06-18 14:38:07.837213-05	2025-06-18 18:34:22.671541-05	f	\N	\N	4501	\N
79	alove@gmail.com	pbkdf2:sha256:1000000$UBWmykEOEErXt3MF$9f4c02f6c25d82b41f6fd420c0988c98b353bc7da7907874dee828159f5149ad	Aud	Love		2025-06-22 06:56:26.054358-05	\N	f	\N	\N	4501	\N
72	sosterman@gmail.com	pbkdf2:sha256:1000000$8enuEe5NBXOwpuEl$fb803ada45e3322c95a7d9058232406e52cc51b89c4e6cb6a8050e54e9883606	Scott	Osterman	\N	2025-06-18 19:29:20.268252-05	2025-06-20 13:26:30.038807-05	f	\N	\N	4501	\N
404	olga@gmail.com	pbkdf2:sha256:1000000$A768UiVFEhdECPHG$24b648adb1487325bc67b3e70ea03462cb90a1f952ce7b8f758c2c6f29fb5a67	Olga	Martinsone	\N	2025-06-24 07:10:37.532588-05	\N	f	Deuce	Righty	4501	\N
77	jessfreedman@gmail.com	pbkdf2:sha256:1000000$1ls6ndborMDlMZPq$0a6ed95b0170a5bde9a8f97f55e712ddb23601548eaea0790cdb72b3a96d44af	Jessica	Freedman		2025-06-21 12:43:42.446194-05	2025-06-22 07:38:04.759402-05	f	\N	\N	4501	\N
76	lwagner@gmail.com	pbkdf2:sha256:1000000$UbtdfMh90YqjYkyM$d438598699564764660f72e5a3951a037671ec414d6bc5f5af966a29eeecd4ca	Lisa	Wagner	\N	2025-06-20 16:03:21.313314-05	2025-06-22 07:39:11.763817-05	f	\N	\N	4501	\N
161	bfox@gmail.com	pbkdf2:sha256:1000000$upzO5uQDtPLIQYIp$749256b483cd8207d67b8f2c42d0ab6446eef45e9f45d6bc27711251ee53894e	Brian	Fox	\N	2025-06-22 13:05:47.164307-05	2025-06-22 17:21:24.602276-05	f	\N	\N	4501	\N
403	rjarol@gmail.com	pbkdf2:sha256:1000000$xtonv9wq10M2YB4y$e6c38eb1c2461d72ab5a022a5f47b08e5074131c4fc6e91e32d556adf8238872	Ryan	Jarol	\N	2025-06-23 22:32:07.056969-05	2025-06-23 22:33:09.977431-05	f	Ad	Righty	4501	\N
350	rwerman@gmail.com	pbkdf2:sha256:1000000$wniAbkSPoh5V8yKE$137d97b3172ac06b025a010fa8c6a218ba751e9e8d6a4a6b3edfdbd3ee2d9a16	Rob	Werman		2025-06-23 16:47:23.157448-05	2025-06-23 21:00:36.401014-05	f	Either	Lefty	4501	\N
357	gswender@gmail.com	pbkdf2:sha256:1000000$0FhWrZ48iHg3ZKZE$723fcbbbf9a7e40f0de4c66eb611a9e662c3900a257196d031bf644abb7bb2d6	G	Swender		2025-06-23 21:40:17.851166-05	\N	f			4501	\N
399	gswender@gmai.com	pbkdf2:sha256:1000000$nUgaHsMRdDArvRWD$8d9825c4b15b94d29713c92e8650407ef77bf970e7a68fe845281e68a5cd617a	ggg	Swender		2025-06-23 22:01:16.941956-05	\N	f	Deuce	Lefty	4501	\N
349	hdakoff@gmail.com	pbkdf2:sha256:1000000$5r72qnkonMVOBhUc$22e5422b6830907f9c6c8f2790e28c1f992d1f692f1fe8bf94d80ad652f3e7ff	Howard	Dakoff		2025-06-23 16:00:49.844705-05	\N	f	Ad	Righty	4501	\N
352	daranberg@gmail.com	pbkdf2:sha256:1000000$adB1nmEuKIRs4aLj$1493dd44b9dc194c8fc368ae55700305b5739e2ed76b2c82ce71570934a36945	Dave	Arenberg	\N	2025-06-23 21:30:47.038437-05	\N	f	\N	\N	4501	\N
356	gswender1@gmail.com	pbkdf2:sha256:1000000$lKfMMbhqQAl7ioqE$aacc76702b19ff038e3dbe3fcce4f37e685e1ef2fbeb14b6940fe45a6a97df56	Gregori	Swender		2025-06-23 21:35:37.88671-05	\N	f			4501	\N
409	pkatai@gmail.com	pbkdf2:sha256:1000000$9zNKmmWekFgG65rw$4e009c566878e353db5fff6f6fea3065086f30f0081a9618f9212c5e65d18d01	P	Katai	\N	2025-06-24 15:54:02.759624-05	\N	f	Deuce	Righty	4501	\N
43	rossfreedman@gmail.com	pbkdf2:sha256:1000000$Oo2fmSFhklWs3uHQ$e69e6fcb13534ebcb147025e83113f17c452f65184e75ac680f7757198191ea2	Ross	Freedman		2025-06-13 07:56:06.90276-05	2025-06-24 18:10:28.768047-05	t	Ad	Righty	4501	\N
49	vforman@gmail.com	pbkdf2:sha256:1000000$caxRWnaQoWXcdlyk$63f01381a3ea8fe3acfb29418ad8154a2571848269c485163c11cb49a51d7f86	Victor	Forman		2025-06-13 20:32:46.728153-05	2025-06-24 19:45:21.827639-05	f	Deuce	Righty	4501	\N
\.


--
-- TOC entry 4219 (class 0 OID 0)
-- Dependencies: 219
-- Name: club_leagues_id_seq; Type: SEQUENCE SET; Schema: public; Owner: -
--

SELECT pg_catalog.setval('public.club_leagues_id_seq', 79509, true);


--
-- TOC entry 4220 (class 0 OID 0)
-- Dependencies: 221
-- Name: clubs_id_seq; Type: SEQUENCE SET; Schema: public; Owner: -
--

SELECT pg_catalog.setval('public.clubs_id_seq', 4649, true);


--
-- TOC entry 4221 (class 0 OID 0)
-- Dependencies: 223
-- Name: leagues_id_seq; Type: SEQUENCE SET; Schema: public; Owner: -
--

SELECT pg_catalog.setval('public.leagues_id_seq', 4517, true);


--
-- TOC entry 4222 (class 0 OID 0)
-- Dependencies: 225
-- Name: match_scores_id_seq; Type: SEQUENCE SET; Schema: public; Owner: -
--

SELECT pg_catalog.setval('public.match_scores_id_seq', 770298, true);


--
-- TOC entry 4223 (class 0 OID 0)
-- Dependencies: 231
-- Name: player_availability_id_seq; Type: SEQUENCE SET; Schema: public; Owner: -
--

SELECT pg_catalog.setval('public.player_availability_id_seq', 194, true);


--
-- TOC entry 4224 (class 0 OID 0)
-- Dependencies: 233
-- Name: player_history_id_seq; Type: SEQUENCE SET; Schema: public; Owner: -
--

SELECT pg_catalog.setval('public.player_history_id_seq', 14299654, true);


--
-- TOC entry 4225 (class 0 OID 0)
-- Dependencies: 235
-- Name: player_season_tracking_id_seq; Type: SEQUENCE SET; Schema: public; Owner: -
--

SELECT pg_catalog.setval('public.player_season_tracking_id_seq', 78, true);


--
-- TOC entry 4226 (class 0 OID 0)
-- Dependencies: 237
-- Name: poll_choices_id_seq; Type: SEQUENCE SET; Schema: public; Owner: -
--

SELECT pg_catalog.setval('public.poll_choices_id_seq', 71, true);


--
-- TOC entry 4227 (class 0 OID 0)
-- Dependencies: 239
-- Name: poll_responses_id_seq; Type: SEQUENCE SET; Schema: public; Owner: -
--

SELECT pg_catalog.setval('public.poll_responses_id_seq', 18, true);


--
-- TOC entry 4228 (class 0 OID 0)
-- Dependencies: 241
-- Name: polls_id_seq; Type: SEQUENCE SET; Schema: public; Owner: -
--

SELECT pg_catalog.setval('public.polls_id_seq', 34, true);


--
-- TOC entry 4229 (class 0 OID 0)
-- Dependencies: 243
-- Name: pro_lessons_id_seq; Type: SEQUENCE SET; Schema: public; Owner: -
--

SELECT pg_catalog.setval('public.pro_lessons_id_seq', 1, false);


--
-- TOC entry 4230 (class 0 OID 0)
-- Dependencies: 245
-- Name: pros_id_seq; Type: SEQUENCE SET; Schema: public; Owner: -
--

SELECT pg_catalog.setval('public.pros_id_seq', 7, true);


--
-- TOC entry 4231 (class 0 OID 0)
-- Dependencies: 247
-- Name: schedule_id_seq; Type: SEQUENCE SET; Schema: public; Owner: -
--

SELECT pg_catalog.setval('public.schedule_id_seq', 130589, true);


--
-- TOC entry 4232 (class 0 OID 0)
-- Dependencies: 249
-- Name: series_id_seq; Type: SEQUENCE SET; Schema: public; Owner: -
--

SELECT pg_catalog.setval('public.series_id_seq', 4466, true);


--
-- TOC entry 4233 (class 0 OID 0)
-- Dependencies: 251
-- Name: series_leagues_id_seq; Type: SEQUENCE SET; Schema: public; Owner: -
--

SELECT pg_catalog.setval('public.series_leagues_id_seq', 3728, true);


--
-- TOC entry 4234 (class 0 OID 0)
-- Dependencies: 253
-- Name: series_name_mappings_id_seq; Type: SEQUENCE SET; Schema: public; Owner: -
--

SELECT pg_catalog.setval('public.series_name_mappings_id_seq', 38, true);


--
-- TOC entry 4235 (class 0 OID 0)
-- Dependencies: 255
-- Name: series_stats_id_seq; Type: SEQUENCE SET; Schema: public; Owner: -
--

SELECT pg_catalog.setval('public.series_stats_id_seq', 30979, true);


--
-- TOC entry 4236 (class 0 OID 0)
-- Dependencies: 257
-- Name: team_format_mappings_id_seq; Type: SEQUENCE SET; Schema: public; Owner: -
--

SELECT pg_catalog.setval('public.team_format_mappings_id_seq', 210, true);


--
-- TOC entry 4237 (class 0 OID 0)
-- Dependencies: 259
-- Name: teams_id_seq; Type: SEQUENCE SET; Schema: public; Owner: -
--

SELECT pg_catalog.setval('public.teams_id_seq', 14131, true);


--
-- TOC entry 4238 (class 0 OID 0)
-- Dependencies: 261
-- Name: user_activity_logs_id_seq; Type: SEQUENCE SET; Schema: public; Owner: -
--

SELECT pg_catalog.setval('public.user_activity_logs_id_seq', 10765, true);


--
-- TOC entry 4239 (class 0 OID 0)
-- Dependencies: 263
-- Name: user_instructions_id_seq; Type: SEQUENCE SET; Schema: public; Owner: -
--

SELECT pg_catalog.setval('public.user_instructions_id_seq', 14, true);


--
-- TOC entry 4240 (class 0 OID 0)
-- Dependencies: 264
-- Name: users_id_seq; Type: SEQUENCE SET; Schema: public; Owner: -
--

SELECT pg_catalog.setval('public.users_id_seq', 328601, true);


--
-- TOC entry 4241 (class 0 OID 0)
-- Dependencies: 265
-- Name: users_id_seq1; Type: SEQUENCE SET; Schema: public; Owner: -
--

SELECT pg_catalog.setval('public.users_id_seq1', 409, true);


--
-- TOC entry 3857 (class 2606 OID 46661)
-- Name: activity_log activity_log_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.activity_log
    ADD CONSTRAINT activity_log_pkey PRIMARY KEY (id);


--
-- TOC entry 3859 (class 2606 OID 46663)
-- Name: alembic_version alembic_version_pkc; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.alembic_version
    ADD CONSTRAINT alembic_version_pkc PRIMARY KEY (version_num);


--
-- TOC entry 3861 (class 2606 OID 46665)
-- Name: club_leagues club_leagues_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.club_leagues
    ADD CONSTRAINT club_leagues_pkey PRIMARY KEY (id);


--
-- TOC entry 3867 (class 2606 OID 46667)
-- Name: clubs clubs_name_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.clubs
    ADD CONSTRAINT clubs_name_key UNIQUE (name);


--
-- TOC entry 3869 (class 2606 OID 46669)
-- Name: clubs clubs_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.clubs
    ADD CONSTRAINT clubs_pkey PRIMARY KEY (id);


--
-- TOC entry 3872 (class 2606 OID 46671)
-- Name: leagues leagues_league_id_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.leagues
    ADD CONSTRAINT leagues_league_id_key UNIQUE (league_id);


--
-- TOC entry 3874 (class 2606 OID 46673)
-- Name: leagues leagues_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.leagues
    ADD CONSTRAINT leagues_pkey PRIMARY KEY (id);


--
-- TOC entry 3876 (class 2606 OID 46675)
-- Name: match_scores match_scores_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.match_scores
    ADD CONSTRAINT match_scores_pkey PRIMARY KEY (id);


--
-- TOC entry 3890 (class 2606 OID 46677)
-- Name: player_availability player_availability_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.player_availability
    ADD CONSTRAINT player_availability_pkey PRIMARY KEY (id);


--
-- TOC entry 3894 (class 2606 OID 46679)
-- Name: player_history player_history_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.player_history
    ADD CONSTRAINT player_history_pkey PRIMARY KEY (id);


--
-- TOC entry 3896 (class 2606 OID 46681)
-- Name: player_season_tracking player_season_tracking_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.player_season_tracking
    ADD CONSTRAINT player_season_tracking_pkey PRIMARY KEY (id);


--
-- TOC entry 3900 (class 2606 OID 46683)
-- Name: poll_choices poll_choices_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.poll_choices
    ADD CONSTRAINT poll_choices_pkey PRIMARY KEY (id);


--
-- TOC entry 3902 (class 2606 OID 46685)
-- Name: poll_responses poll_responses_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.poll_responses
    ADD CONSTRAINT poll_responses_pkey PRIMARY KEY (id);


--
-- TOC entry 3906 (class 2606 OID 46687)
-- Name: polls polls_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.polls
    ADD CONSTRAINT polls_pkey PRIMARY KEY (id);


--
-- TOC entry 3911 (class 2606 OID 46689)
-- Name: pro_lessons pro_lessons_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.pro_lessons
    ADD CONSTRAINT pro_lessons_pkey PRIMARY KEY (id);


--
-- TOC entry 3914 (class 2606 OID 46691)
-- Name: pros pros_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.pros
    ADD CONSTRAINT pros_pkey PRIMARY KEY (id);


--
-- TOC entry 3916 (class 2606 OID 46693)
-- Name: schedule schedule_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.schedule
    ADD CONSTRAINT schedule_pkey PRIMARY KEY (id);


--
-- TOC entry 3922 (class 2606 OID 46695)
-- Name: series_leagues series_leagues_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.series_leagues
    ADD CONSTRAINT series_leagues_pkey PRIMARY KEY (id);


--
-- TOC entry 3918 (class 2606 OID 46697)
-- Name: series series_name_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.series
    ADD CONSTRAINT series_name_key UNIQUE (name);


--
-- TOC entry 3927 (class 2606 OID 46699)
-- Name: series_name_mappings series_name_mappings_league_id_user_series_name_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.series_name_mappings
    ADD CONSTRAINT series_name_mappings_league_id_user_series_name_key UNIQUE (league_id, user_series_name);


--
-- TOC entry 3929 (class 2606 OID 46701)
-- Name: series_name_mappings series_name_mappings_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.series_name_mappings
    ADD CONSTRAINT series_name_mappings_pkey PRIMARY KEY (id);


--
-- TOC entry 3920 (class 2606 OID 46703)
-- Name: series series_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.series
    ADD CONSTRAINT series_pkey PRIMARY KEY (id);


--
-- TOC entry 3931 (class 2606 OID 46705)
-- Name: series_stats series_stats_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.series_stats
    ADD CONSTRAINT series_stats_pkey PRIMARY KEY (id);


--
-- TOC entry 3935 (class 2606 OID 46707)
-- Name: team_format_mappings team_format_mappings_league_id_user_input_format_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.team_format_mappings
    ADD CONSTRAINT team_format_mappings_league_id_user_input_format_key UNIQUE (league_id, user_input_format);


--
-- TOC entry 3937 (class 2606 OID 46709)
-- Name: team_format_mappings team_format_mappings_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.team_format_mappings
    ADD CONSTRAINT team_format_mappings_pkey PRIMARY KEY (id);


--
-- TOC entry 3939 (class 2606 OID 46711)
-- Name: teams teams_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.teams
    ADD CONSTRAINT teams_pkey PRIMARY KEY (id);


--
-- TOC entry 3865 (class 2606 OID 46713)
-- Name: club_leagues unique_club_league; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.club_leagues
    ADD CONSTRAINT unique_club_league UNIQUE (club_id, league_id);


--
-- TOC entry 3892 (class 2606 OID 46715)
-- Name: player_availability unique_player_availability; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.player_availability
    ADD CONSTRAINT unique_player_availability UNIQUE (player_name, match_date, series_id);


--
-- TOC entry 3878 (class 2606 OID 46717)
-- Name: players unique_player_in_league_club_series; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.players
    ADD CONSTRAINT unique_player_in_league_club_series UNIQUE (tenniscores_player_id, league_id, club_id, series_id);


--
-- TOC entry 3898 (class 2606 OID 46719)
-- Name: player_season_tracking unique_player_season_tracking; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.player_season_tracking
    ADD CONSTRAINT unique_player_season_tracking UNIQUE (player_id, league_id, season_year);


--
-- TOC entry 3904 (class 2606 OID 46721)
-- Name: poll_responses unique_poll_player_response; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.poll_responses
    ADD CONSTRAINT unique_poll_player_response UNIQUE (poll_id, player_id);


--
-- TOC entry 3924 (class 2606 OID 46723)
-- Name: series_leagues unique_series_league; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.series_leagues
    ADD CONSTRAINT unique_series_league UNIQUE (series_id, league_id);


--
-- TOC entry 3941 (class 2606 OID 46725)
-- Name: teams unique_team_club_series_league; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.teams
    ADD CONSTRAINT unique_team_club_series_league UNIQUE (club_id, series_id, league_id);


--
-- TOC entry 3943 (class 2606 OID 46727)
-- Name: teams unique_team_name_per_league; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.teams
    ADD CONSTRAINT unique_team_name_per_league UNIQUE (team_name, league_id);


--
-- TOC entry 3945 (class 2606 OID 46729)
-- Name: user_activity_logs user_activity_logs_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.user_activity_logs
    ADD CONSTRAINT user_activity_logs_pkey PRIMARY KEY (id);


--
-- TOC entry 3947 (class 2606 OID 46731)
-- Name: user_instructions user_instructions_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.user_instructions
    ADD CONSTRAINT user_instructions_pkey PRIMARY KEY (id);


--
-- TOC entry 3882 (class 2606 OID 46733)
-- Name: user_player_associations user_player_associations_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.user_player_associations
    ADD CONSTRAINT user_player_associations_pkey PRIMARY KEY (user_id, tenniscores_player_id);


--
-- TOC entry 3886 (class 2606 OID 46735)
-- Name: users users_email_key1; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.users
    ADD CONSTRAINT users_email_key1 UNIQUE (email);


--
-- TOC entry 3880 (class 2606 OID 46737)
-- Name: players users_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.players
    ADD CONSTRAINT users_pkey PRIMARY KEY (id);


--
-- TOC entry 3888 (class 2606 OID 46739)
-- Name: users users_pkey1; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.users
    ADD CONSTRAINT users_pkey1 PRIMARY KEY (id);


--
-- TOC entry 3862 (class 1259 OID 46928)
-- Name: idx_club_leagues_club_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_club_leagues_club_id ON public.club_leagues USING btree (club_id);


--
-- TOC entry 3863 (class 1259 OID 46929)
-- Name: idx_club_leagues_league_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_club_leagues_league_id ON public.club_leagues USING btree (league_id);


--
-- TOC entry 3870 (class 1259 OID 46927)
-- Name: idx_leagues_league_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_leagues_league_id ON public.leagues USING btree (league_id);


--
-- TOC entry 3907 (class 1259 OID 46740)
-- Name: idx_pro_lessons_lesson_date; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_pro_lessons_lesson_date ON public.pro_lessons USING btree (lesson_date);


--
-- TOC entry 3908 (class 1259 OID 46741)
-- Name: idx_pro_lessons_status; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_pro_lessons_status ON public.pro_lessons USING btree (status);


--
-- TOC entry 3909 (class 1259 OID 46742)
-- Name: idx_pro_lessons_user_email; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_pro_lessons_user_email ON public.pro_lessons USING btree (user_email);


--
-- TOC entry 3912 (class 1259 OID 46743)
-- Name: idx_pros_active; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_pros_active ON public.pros USING btree (is_active);


--
-- TOC entry 3925 (class 1259 OID 46744)
-- Name: idx_series_mappings_lookup; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_series_mappings_lookup ON public.series_name_mappings USING btree (league_id, user_series_name);


--
-- TOC entry 3932 (class 1259 OID 46745)
-- Name: idx_team_format_mappings_active; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_team_format_mappings_active ON public.team_format_mappings USING btree (league_id, is_active);


--
-- TOC entry 3933 (class 1259 OID 46746)
-- Name: idx_team_format_mappings_lookup; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_team_format_mappings_lookup ON public.team_format_mappings USING btree (league_id, user_input_format);


--
-- TOC entry 3883 (class 1259 OID 46930)
-- Name: idx_users_league_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_users_league_id ON public.users USING btree (league_id);


--
-- TOC entry 3884 (class 1259 OID 46931)
-- Name: idx_users_tenniscores_player_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_users_tenniscores_player_id ON public.users USING btree (tenniscores_player_id);


--
-- TOC entry 3984 (class 2620 OID 46747)
-- Name: player_availability trigger_auto_populate_player_id; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER trigger_auto_populate_player_id BEFORE INSERT ON public.player_availability FOR EACH ROW EXECUTE FUNCTION public.auto_populate_player_id();


--
-- TOC entry 3985 (class 2620 OID 46748)
-- Name: player_season_tracking trigger_update_player_season_tracking_updated_at; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER trigger_update_player_season_tracking_updated_at BEFORE UPDATE ON public.player_season_tracking FOR EACH ROW EXECUTE FUNCTION public.update_player_season_tracking_updated_at();


--
-- TOC entry 3981 (class 2620 OID 46749)
-- Name: clubs update_clubs_updated_at; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER update_clubs_updated_at BEFORE UPDATE ON public.clubs FOR EACH ROW EXECUTE FUNCTION public.update_updated_at_column();


--
-- TOC entry 3982 (class 2620 OID 46750)
-- Name: leagues update_leagues_updated_at; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER update_leagues_updated_at BEFORE UPDATE ON public.leagues FOR EACH ROW EXECUTE FUNCTION public.update_updated_at_column();


--
-- TOC entry 3983 (class 2620 OID 46751)
-- Name: players update_players_updated_at; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER update_players_updated_at BEFORE UPDATE ON public.players FOR EACH ROW EXECUTE FUNCTION public.update_updated_at_column();


--
-- TOC entry 3986 (class 2620 OID 46752)
-- Name: series update_series_updated_at; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER update_series_updated_at BEFORE UPDATE ON public.series FOR EACH ROW EXECUTE FUNCTION public.update_updated_at_column();


--
-- TOC entry 3987 (class 2620 OID 46753)
-- Name: teams update_teams_updated_at; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER update_teams_updated_at BEFORE UPDATE ON public.teams FOR EACH ROW EXECUTE FUNCTION public.update_teams_updated_at_column();


--
-- TOC entry 3948 (class 2606 OID 46754)
-- Name: activity_log activity_log_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.activity_log
    ADD CONSTRAINT activity_log_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(id);


--
-- TOC entry 3949 (class 2606 OID 46759)
-- Name: club_leagues club_leagues_club_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.club_leagues
    ADD CONSTRAINT club_leagues_club_id_fkey FOREIGN KEY (club_id) REFERENCES public.clubs(id);


--
-- TOC entry 3950 (class 2606 OID 46764)
-- Name: club_leagues club_leagues_league_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.club_leagues
    ADD CONSTRAINT club_leagues_league_id_fkey FOREIGN KEY (league_id) REFERENCES public.leagues(id);


--
-- TOC entry 3951 (class 2606 OID 46769)
-- Name: match_scores fk_match_scores_league_id; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.match_scores
    ADD CONSTRAINT fk_match_scores_league_id FOREIGN KEY (league_id) REFERENCES public.leagues(id);


--
-- TOC entry 3960 (class 2606 OID 46774)
-- Name: player_history fk_player_history_league_id; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.player_history
    ADD CONSTRAINT fk_player_history_league_id FOREIGN KEY (league_id) REFERENCES public.leagues(id);


--
-- TOC entry 3961 (class 2606 OID 46779)
-- Name: player_history fk_player_history_player_id; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.player_history
    ADD CONSTRAINT fk_player_history_player_id FOREIGN KEY (player_id) REFERENCES public.players(id);


--
-- TOC entry 3967 (class 2606 OID 46784)
-- Name: schedule fk_schedule_league_id; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.schedule
    ADD CONSTRAINT fk_schedule_league_id FOREIGN KEY (league_id) REFERENCES public.leagues(id);


--
-- TOC entry 3972 (class 2606 OID 46789)
-- Name: series_name_mappings fk_series_mappings_league; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.series_name_mappings
    ADD CONSTRAINT fk_series_mappings_league FOREIGN KEY (league_id) REFERENCES public.leagues(league_id) ON DELETE CASCADE;


--
-- TOC entry 3973 (class 2606 OID 46794)
-- Name: series_stats fk_series_stats_league_id; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.series_stats
    ADD CONSTRAINT fk_series_stats_league_id FOREIGN KEY (league_id) REFERENCES public.leagues(id);


--
-- TOC entry 3975 (class 2606 OID 46799)
-- Name: team_format_mappings fk_team_format_mappings_league; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.team_format_mappings
    ADD CONSTRAINT fk_team_format_mappings_league FOREIGN KEY (league_id) REFERENCES public.leagues(league_id) ON DELETE CASCADE;


--
-- TOC entry 3958 (class 2606 OID 46804)
-- Name: user_player_associations fk_upa_user_id; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.user_player_associations
    ADD CONSTRAINT fk_upa_user_id FOREIGN KEY (user_id) REFERENCES public.users(id);


--
-- TOC entry 3979 (class 2606 OID 46809)
-- Name: user_instructions fk_user_instructions_team_id; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.user_instructions
    ADD CONSTRAINT fk_user_instructions_team_id FOREIGN KEY (team_id) REFERENCES public.teams(id);


--
-- TOC entry 3952 (class 2606 OID 46814)
-- Name: match_scores match_scores_away_team_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.match_scores
    ADD CONSTRAINT match_scores_away_team_id_fkey FOREIGN KEY (away_team_id) REFERENCES public.teams(id);


--
-- TOC entry 3953 (class 2606 OID 46819)
-- Name: match_scores match_scores_home_team_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.match_scores
    ADD CONSTRAINT match_scores_home_team_id_fkey FOREIGN KEY (home_team_id) REFERENCES public.teams(id);


--
-- TOC entry 3954 (class 2606 OID 46824)
-- Name: players players_league_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.players
    ADD CONSTRAINT players_league_id_fkey FOREIGN KEY (league_id) REFERENCES public.leagues(id);


--
-- TOC entry 3955 (class 2606 OID 46829)
-- Name: players players_team_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.players
    ADD CONSTRAINT players_team_id_fkey FOREIGN KEY (team_id) REFERENCES public.teams(id);


--
-- TOC entry 3962 (class 2606 OID 46834)
-- Name: poll_choices poll_choices_poll_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.poll_choices
    ADD CONSTRAINT poll_choices_poll_id_fkey FOREIGN KEY (poll_id) REFERENCES public.polls(id) ON DELETE CASCADE;


--
-- TOC entry 3963 (class 2606 OID 46839)
-- Name: poll_responses poll_responses_choice_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.poll_responses
    ADD CONSTRAINT poll_responses_choice_id_fkey FOREIGN KEY (choice_id) REFERENCES public.poll_choices(id);


--
-- TOC entry 3964 (class 2606 OID 46844)
-- Name: poll_responses poll_responses_poll_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.poll_responses
    ADD CONSTRAINT poll_responses_poll_id_fkey FOREIGN KEY (poll_id) REFERENCES public.polls(id) ON DELETE CASCADE;


--
-- TOC entry 3965 (class 2606 OID 46849)
-- Name: polls polls_created_by_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.polls
    ADD CONSTRAINT polls_created_by_fkey FOREIGN KEY (created_by) REFERENCES public.users(id);


--
-- TOC entry 3966 (class 2606 OID 46854)
-- Name: pro_lessons pro_lessons_pro_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.pro_lessons
    ADD CONSTRAINT pro_lessons_pro_id_fkey FOREIGN KEY (pro_id) REFERENCES public.pros(id);


--
-- TOC entry 3968 (class 2606 OID 46859)
-- Name: schedule schedule_away_team_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.schedule
    ADD CONSTRAINT schedule_away_team_id_fkey FOREIGN KEY (away_team_id) REFERENCES public.teams(id);


--
-- TOC entry 3969 (class 2606 OID 46864)
-- Name: schedule schedule_home_team_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.schedule
    ADD CONSTRAINT schedule_home_team_id_fkey FOREIGN KEY (home_team_id) REFERENCES public.teams(id);


--
-- TOC entry 3970 (class 2606 OID 46869)
-- Name: series_leagues series_leagues_league_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.series_leagues
    ADD CONSTRAINT series_leagues_league_id_fkey FOREIGN KEY (league_id) REFERENCES public.leagues(id);


--
-- TOC entry 3971 (class 2606 OID 46874)
-- Name: series_leagues series_leagues_series_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.series_leagues
    ADD CONSTRAINT series_leagues_series_id_fkey FOREIGN KEY (series_id) REFERENCES public.series(id);


--
-- TOC entry 3974 (class 2606 OID 46879)
-- Name: series_stats series_stats_team_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.series_stats
    ADD CONSTRAINT series_stats_team_id_fkey FOREIGN KEY (team_id) REFERENCES public.teams(id);


--
-- TOC entry 3976 (class 2606 OID 46884)
-- Name: teams teams_club_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.teams
    ADD CONSTRAINT teams_club_id_fkey FOREIGN KEY (club_id) REFERENCES public.clubs(id);


--
-- TOC entry 3977 (class 2606 OID 46889)
-- Name: teams teams_league_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.teams
    ADD CONSTRAINT teams_league_id_fkey FOREIGN KEY (league_id) REFERENCES public.leagues(id);


--
-- TOC entry 3978 (class 2606 OID 46894)
-- Name: teams teams_series_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.teams
    ADD CONSTRAINT teams_series_id_fkey FOREIGN KEY (series_id) REFERENCES public.series(id);


--
-- TOC entry 3980 (class 2606 OID 46899)
-- Name: user_instructions user_instructions_series_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.user_instructions
    ADD CONSTRAINT user_instructions_series_id_fkey FOREIGN KEY (series_id) REFERENCES public.series(id);


--
-- TOC entry 3956 (class 2606 OID 46904)
-- Name: players users_club_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.players
    ADD CONSTRAINT users_club_id_fkey FOREIGN KEY (club_id) REFERENCES public.clubs(id);


--
-- TOC entry 3959 (class 2606 OID 46922)
-- Name: users users_league_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.users
    ADD CONSTRAINT users_league_id_fkey FOREIGN KEY (league_id) REFERENCES public.leagues(id);


--
-- TOC entry 3957 (class 2606 OID 46909)
-- Name: players users_series_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.players
    ADD CONSTRAINT users_series_id_fkey FOREIGN KEY (series_id) REFERENCES public.series(id);


-- Completed on 2025-06-24 19:50:37 CDT

--
-- PostgreSQL database dump complete
--

