--
-- PostgreSQL database dump
--

-- Dumped from database version 16.8 (Debian 16.8-1.pgdg120+1)
-- Dumped by pg_dump version 16.9 (Homebrew)

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
-- Name: update_pickup_games_updated_at(); Type: FUNCTION; Schema: public; Owner: -
--

CREATE FUNCTION public.update_pickup_games_updated_at() RETURNS trigger
    LANGUAGE plpgsql
    AS $$
    BEGIN
        NEW.updated_at = CURRENT_TIMESTAMP;
        RETURN NEW;
    END;
    $$;


--
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
-- Name: alembic_version; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.alembic_version (
    version_num character varying(32) NOT NULL
);


--
-- Name: club_leagues; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.club_leagues (
    id integer NOT NULL,
    club_id integer NOT NULL,
    league_id integer NOT NULL,
    created_at timestamp with time zone DEFAULT CURRENT_TIMESTAMP
);


--
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
-- Name: club_leagues_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.club_leagues_id_seq OWNED BY public.club_leagues.id;


--
-- Name: clubs; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.clubs (
    id integer NOT NULL,
    name character varying(255) NOT NULL,
    updated_at timestamp with time zone DEFAULT CURRENT_TIMESTAMP,
    club_address character varying(500),
    logo_filename character varying(500)
);


--
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
-- Name: clubs_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.clubs_id_seq OWNED BY public.clubs.id;


--
-- Name: group_members; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.group_members (
    id integer NOT NULL,
    group_id integer NOT NULL,
    user_id integer NOT NULL,
    added_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP,
    added_by_user_id integer NOT NULL
);


--
-- Name: group_members_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.group_members_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: group_members_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.group_members_id_seq OWNED BY public.group_members.id;


--
-- Name: groups; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.groups (
    id integer NOT NULL,
    name character varying(255) NOT NULL,
    description text,
    creator_user_id integer NOT NULL,
    created_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP,
    updated_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP
);


--
-- Name: groups_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.groups_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: groups_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.groups_id_seq OWNED BY public.groups.id;


--
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
-- Name: leagues_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.leagues_id_seq OWNED BY public.leagues.id;


--
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
-- Name: match_scores_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.match_scores_id_seq OWNED BY public.match_scores.id;


--
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
-- Name: user_player_associations; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.user_player_associations (
    user_id integer NOT NULL,
    is_primary boolean DEFAULT false,
    created_at timestamp with time zone DEFAULT CURRENT_TIMESTAMP,
    tenniscores_player_id character varying(255) NOT NULL
);


--
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
    tenniscores_player_id character varying(255),
    league_context integer
);


--
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
-- Name: pickup_game_participants; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.pickup_game_participants (
    id integer NOT NULL,
    pickup_game_id integer NOT NULL,
    user_id integer NOT NULL,
    joined_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP
);


--
-- Name: pickup_game_participants_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.pickup_game_participants_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: pickup_game_participants_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.pickup_game_participants_id_seq OWNED BY public.pickup_game_participants.id;


--
-- Name: pickup_games; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.pickup_games (
    id integer NOT NULL,
    description text NOT NULL,
    game_date date NOT NULL,
    game_time time without time zone NOT NULL,
    players_requested integer NOT NULL,
    players_committed integer DEFAULT 0 NOT NULL,
    pti_low integer DEFAULT '-30'::integer NOT NULL,
    pti_high integer DEFAULT 100 NOT NULL,
    series_low integer,
    series_high integer,
    club_only boolean DEFAULT false NOT NULL,
    creator_user_id integer,
    created_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP,
    updated_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT ck_players_committed_non_negative CHECK ((players_committed >= 0)),
    CONSTRAINT ck_players_requested_positive CHECK ((players_requested > 0)),
    CONSTRAINT ck_valid_player_counts CHECK ((players_committed <= players_requested)),
    CONSTRAINT ck_valid_pti_range CHECK ((pti_low <= pti_high)),
    CONSTRAINT ck_valid_series_range CHECK (((series_low IS NULL) OR (series_high IS NULL) OR (series_low <= series_high)))
);


--
-- Name: pickup_games_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.pickup_games_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: pickup_games_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.pickup_games_id_seq OWNED BY public.pickup_games.id;


--
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
    user_id integer,
    CONSTRAINT match_date_must_be_midnight_utc CHECK (((date_part('hour'::text, (match_date AT TIME ZONE 'UTC'::text)) = (0)::double precision) AND (date_part('minute'::text, (match_date AT TIME ZONE 'UTC'::text)) = (0)::double precision) AND (date_part('second'::text, (match_date AT TIME ZONE 'UTC'::text)) = (0)::double precision))),
    CONSTRAINT valid_availability_status CHECK ((availability_status = ANY (ARRAY[1, 2, 3])))
);


--
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
-- Name: player_availability_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.player_availability_id_seq OWNED BY public.player_availability.id;


--
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
-- Name: player_history_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.player_history_id_seq OWNED BY public.player_history.id;


--
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
-- Name: player_season_tracking_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.player_season_tracking_id_seq OWNED BY public.player_season_tracking.id;


--
-- Name: poll_choices; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.poll_choices (
    id integer NOT NULL,
    poll_id integer,
    choice_text text NOT NULL
);


--
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
-- Name: poll_choices_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.poll_choices_id_seq OWNED BY public.poll_choices.id;


--
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
-- Name: poll_responses_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.poll_responses_id_seq OWNED BY public.poll_responses.id;


--
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
-- Name: polls_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.polls_id_seq OWNED BY public.polls.id;


--
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
-- Name: pro_lessons_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.pro_lessons_id_seq OWNED BY public.pro_lessons.id;


--
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
-- Name: pros_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.pros_id_seq OWNED BY public.pros.id;


--
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
-- Name: schedule_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.schedule_id_seq OWNED BY public.schedule.id;


--
-- Name: series; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.series (
    id integer NOT NULL,
    name character varying(255) NOT NULL,
    updated_at timestamp with time zone DEFAULT CURRENT_TIMESTAMP,
    display_name character varying(255) NOT NULL
);


--
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
-- Name: series_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.series_id_seq OWNED BY public.series.id;


--
-- Name: series_leagues; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.series_leagues (
    id integer NOT NULL,
    series_id integer NOT NULL,
    league_id integer NOT NULL,
    created_at timestamp with time zone DEFAULT CURRENT_TIMESTAMP
);


--
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
-- Name: series_leagues_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.series_leagues_id_seq OWNED BY public.series_leagues.id;


--
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
    team_id integer,
    series_id integer
);


--
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
-- Name: series_stats_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.series_stats_id_seq OWNED BY public.series_stats.id;


--
-- Name: system_settings; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.system_settings (
    id integer NOT NULL,
    key character varying(100) NOT NULL,
    value text NOT NULL,
    description text,
    created_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP,
    updated_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP
);


--
-- Name: system_settings_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.system_settings_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: system_settings_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.system_settings_id_seq OWNED BY public.system_settings.id;


--
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
    team_alias character varying(255),
    display_name character varying(255) NOT NULL
);


--
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
-- Name: teams_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.teams_id_seq OWNED BY public.teams.id;


--
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
-- Name: user_activity_logs_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.user_activity_logs_id_seq OWNED BY public.user_activity_logs.id;


--
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
-- Name: user_instructions_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.user_instructions_id_seq OWNED BY public.user_instructions.id;


--
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
-- Name: users_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.users_id_seq OWNED BY public.players.id;


--
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
-- Name: users_id_seq1; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.users_id_seq1 OWNED BY public.users.id;


--
-- Name: club_leagues id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.club_leagues ALTER COLUMN id SET DEFAULT nextval('public.club_leagues_id_seq'::regclass);


--
-- Name: clubs id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.clubs ALTER COLUMN id SET DEFAULT nextval('public.clubs_id_seq'::regclass);


--
-- Name: group_members id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.group_members ALTER COLUMN id SET DEFAULT nextval('public.group_members_id_seq'::regclass);


--
-- Name: groups id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.groups ALTER COLUMN id SET DEFAULT nextval('public.groups_id_seq'::regclass);


--
-- Name: leagues id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.leagues ALTER COLUMN id SET DEFAULT nextval('public.leagues_id_seq'::regclass);


--
-- Name: match_scores id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.match_scores ALTER COLUMN id SET DEFAULT nextval('public.match_scores_id_seq'::regclass);


--
-- Name: pickup_game_participants id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.pickup_game_participants ALTER COLUMN id SET DEFAULT nextval('public.pickup_game_participants_id_seq'::regclass);


--
-- Name: pickup_games id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.pickup_games ALTER COLUMN id SET DEFAULT nextval('public.pickup_games_id_seq'::regclass);


--
-- Name: player_availability id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.player_availability ALTER COLUMN id SET DEFAULT nextval('public.player_availability_id_seq'::regclass);


--
-- Name: player_history id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.player_history ALTER COLUMN id SET DEFAULT nextval('public.player_history_id_seq'::regclass);


--
-- Name: player_season_tracking id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.player_season_tracking ALTER COLUMN id SET DEFAULT nextval('public.player_season_tracking_id_seq'::regclass);


--
-- Name: players id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.players ALTER COLUMN id SET DEFAULT nextval('public.users_id_seq'::regclass);


--
-- Name: poll_choices id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.poll_choices ALTER COLUMN id SET DEFAULT nextval('public.poll_choices_id_seq'::regclass);


--
-- Name: poll_responses id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.poll_responses ALTER COLUMN id SET DEFAULT nextval('public.poll_responses_id_seq'::regclass);


--
-- Name: polls id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.polls ALTER COLUMN id SET DEFAULT nextval('public.polls_id_seq'::regclass);


--
-- Name: pro_lessons id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.pro_lessons ALTER COLUMN id SET DEFAULT nextval('public.pro_lessons_id_seq'::regclass);


--
-- Name: pros id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.pros ALTER COLUMN id SET DEFAULT nextval('public.pros_id_seq'::regclass);


--
-- Name: schedule id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.schedule ALTER COLUMN id SET DEFAULT nextval('public.schedule_id_seq'::regclass);


--
-- Name: series id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.series ALTER COLUMN id SET DEFAULT nextval('public.series_id_seq'::regclass);


--
-- Name: series_leagues id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.series_leagues ALTER COLUMN id SET DEFAULT nextval('public.series_leagues_id_seq'::regclass);


--
-- Name: series_stats id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.series_stats ALTER COLUMN id SET DEFAULT nextval('public.series_stats_id_seq'::regclass);


--
-- Name: system_settings id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.system_settings ALTER COLUMN id SET DEFAULT nextval('public.system_settings_id_seq'::regclass);


--
-- Name: teams id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.teams ALTER COLUMN id SET DEFAULT nextval('public.teams_id_seq'::regclass);


--
-- Name: user_activity_logs id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.user_activity_logs ALTER COLUMN id SET DEFAULT nextval('public.user_activity_logs_id_seq'::regclass);


--
-- Name: user_instructions id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.user_instructions ALTER COLUMN id SET DEFAULT nextval('public.user_instructions_id_seq'::regclass);


--
-- Name: users id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.users ALTER COLUMN id SET DEFAULT nextval('public.users_id_seq1'::regclass);


--
-- Name: activity_log activity_log_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.activity_log
    ADD CONSTRAINT activity_log_pkey PRIMARY KEY (id);


--
-- Name: alembic_version alembic_version_pkc; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.alembic_version
    ADD CONSTRAINT alembic_version_pkc PRIMARY KEY (version_num);


--
-- Name: club_leagues club_leagues_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.club_leagues
    ADD CONSTRAINT club_leagues_pkey PRIMARY KEY (id);


--
-- Name: clubs clubs_name_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.clubs
    ADD CONSTRAINT clubs_name_key UNIQUE (name);


--
-- Name: clubs clubs_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.clubs
    ADD CONSTRAINT clubs_pkey PRIMARY KEY (id);


--
-- Name: group_members group_members_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.group_members
    ADD CONSTRAINT group_members_pkey PRIMARY KEY (id);


--
-- Name: groups groups_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.groups
    ADD CONSTRAINT groups_pkey PRIMARY KEY (id);


--
-- Name: leagues leagues_league_id_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.leagues
    ADD CONSTRAINT leagues_league_id_key UNIQUE (league_id);


--
-- Name: leagues leagues_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.leagues
    ADD CONSTRAINT leagues_pkey PRIMARY KEY (id);


--
-- Name: match_scores match_scores_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.match_scores
    ADD CONSTRAINT match_scores_pkey PRIMARY KEY (id);


--
-- Name: pickup_game_participants pickup_game_participants_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.pickup_game_participants
    ADD CONSTRAINT pickup_game_participants_pkey PRIMARY KEY (id);


--
-- Name: pickup_games pickup_games_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.pickup_games
    ADD CONSTRAINT pickup_games_pkey PRIMARY KEY (id);


--
-- Name: player_availability player_availability_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.player_availability
    ADD CONSTRAINT player_availability_pkey PRIMARY KEY (id);


--
-- Name: player_history player_history_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.player_history
    ADD CONSTRAINT player_history_pkey PRIMARY KEY (id);


--
-- Name: player_season_tracking player_season_tracking_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.player_season_tracking
    ADD CONSTRAINT player_season_tracking_pkey PRIMARY KEY (id);


--
-- Name: poll_choices poll_choices_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.poll_choices
    ADD CONSTRAINT poll_choices_pkey PRIMARY KEY (id);


--
-- Name: poll_responses poll_responses_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.poll_responses
    ADD CONSTRAINT poll_responses_pkey PRIMARY KEY (id);


--
-- Name: polls polls_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.polls
    ADD CONSTRAINT polls_pkey PRIMARY KEY (id);


--
-- Name: pro_lessons pro_lessons_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.pro_lessons
    ADD CONSTRAINT pro_lessons_pkey PRIMARY KEY (id);


--
-- Name: pros pros_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.pros
    ADD CONSTRAINT pros_pkey PRIMARY KEY (id);


--
-- Name: schedule schedule_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.schedule
    ADD CONSTRAINT schedule_pkey PRIMARY KEY (id);


--
-- Name: series_leagues series_leagues_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.series_leagues
    ADD CONSTRAINT series_leagues_pkey PRIMARY KEY (id);


--
-- Name: series series_name_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.series
    ADD CONSTRAINT series_name_key UNIQUE (name);


--
-- Name: series series_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.series
    ADD CONSTRAINT series_pkey PRIMARY KEY (id);


--
-- Name: series_stats series_stats_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.series_stats
    ADD CONSTRAINT series_stats_pkey PRIMARY KEY (id);


--
-- Name: system_settings system_settings_key_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.system_settings
    ADD CONSTRAINT system_settings_key_key UNIQUE (key);


--
-- Name: system_settings system_settings_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.system_settings
    ADD CONSTRAINT system_settings_pkey PRIMARY KEY (id);


--
-- Name: teams teams_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.teams
    ADD CONSTRAINT teams_pkey PRIMARY KEY (id);


--
-- Name: pickup_game_participants uc_unique_game_participant; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.pickup_game_participants
    ADD CONSTRAINT uc_unique_game_participant UNIQUE (pickup_game_id, user_id);


--
-- Name: group_members uk_group_members_group_user; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.group_members
    ADD CONSTRAINT uk_group_members_group_user UNIQUE (group_id, user_id);


--
-- Name: club_leagues unique_club_league; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.club_leagues
    ADD CONSTRAINT unique_club_league UNIQUE (club_id, league_id);


--
-- Name: players unique_player_in_league_club_series; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.players
    ADD CONSTRAINT unique_player_in_league_club_series UNIQUE (tenniscores_player_id, league_id, club_id, series_id);


--
-- Name: player_season_tracking unique_player_season_tracking; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.player_season_tracking
    ADD CONSTRAINT unique_player_season_tracking UNIQUE (player_id, league_id, season_year);


--
-- Name: poll_responses unique_poll_player_response; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.poll_responses
    ADD CONSTRAINT unique_poll_player_response UNIQUE (poll_id, player_id);


--
-- Name: series_leagues unique_series_league; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.series_leagues
    ADD CONSTRAINT unique_series_league UNIQUE (series_id, league_id);


--
-- Name: teams unique_team_club_series_league; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.teams
    ADD CONSTRAINT unique_team_club_series_league UNIQUE (club_id, series_id, league_id);


--
-- Name: teams unique_team_name_per_league; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.teams
    ADD CONSTRAINT unique_team_name_per_league UNIQUE (team_name, league_id);


--
-- Name: user_player_associations unique_tenniscores_player_id; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.user_player_associations
    ADD CONSTRAINT unique_tenniscores_player_id UNIQUE (tenniscores_player_id);


--
-- Name: user_activity_logs user_activity_logs_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.user_activity_logs
    ADD CONSTRAINT user_activity_logs_pkey PRIMARY KEY (id);


--
-- Name: user_instructions user_instructions_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.user_instructions
    ADD CONSTRAINT user_instructions_pkey PRIMARY KEY (id);


--
-- Name: user_player_associations user_player_associations_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.user_player_associations
    ADD CONSTRAINT user_player_associations_pkey PRIMARY KEY (user_id, tenniscores_player_id);


--
-- Name: users users_email_key1; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.users
    ADD CONSTRAINT users_email_key1 UNIQUE (email);


--
-- Name: players users_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.players
    ADD CONSTRAINT users_pkey PRIMARY KEY (id);


--
-- Name: users users_pkey1; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.users
    ADD CONSTRAINT users_pkey1 PRIMARY KEY (id);


--
-- Name: idx_availability_user_date; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_availability_user_date ON public.player_availability USING btree (user_id, match_date) WHERE (user_id IS NOT NULL);


--
-- Name: idx_club_leagues_club_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_club_leagues_club_id ON public.club_leagues USING btree (club_id);


--
-- Name: idx_club_leagues_league_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_club_leagues_league_id ON public.club_leagues USING btree (league_id);


--
-- Name: idx_group_members_group_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_group_members_group_id ON public.group_members USING btree (group_id);


--
-- Name: idx_group_members_user_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_group_members_user_id ON public.group_members USING btree (user_id);


--
-- Name: idx_groups_creator_user_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_groups_creator_user_id ON public.groups USING btree (creator_user_id);


--
-- Name: idx_leagues_league_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_leagues_league_id ON public.leagues USING btree (league_id);


--
-- Name: idx_pickup_games_creator; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_pickup_games_creator ON public.pickup_games USING btree (creator_user_id);


--
-- Name: idx_pickup_games_date_time; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_pickup_games_date_time ON public.pickup_games USING btree (game_date, game_time);


--
-- Name: idx_pickup_games_status; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_pickup_games_status ON public.pickup_games USING btree (players_requested, players_committed);


--
-- Name: idx_pickup_participants_game; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_pickup_participants_game ON public.pickup_game_participants USING btree (pickup_game_id);


--
-- Name: idx_pickup_participants_user; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_pickup_participants_user ON public.pickup_game_participants USING btree (user_id);


--
-- Name: idx_pro_lessons_lesson_date; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_pro_lessons_lesson_date ON public.pro_lessons USING btree (lesson_date);


--
-- Name: idx_pro_lessons_status; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_pro_lessons_status ON public.pro_lessons USING btree (status);


--
-- Name: idx_pro_lessons_user_email; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_pro_lessons_user_email ON public.pro_lessons USING btree (user_email);


--
-- Name: idx_pros_active; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_pros_active ON public.pros USING btree (is_active);


--
-- Name: idx_series_display_name; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_series_display_name ON public.series USING btree (display_name);


--
-- Name: idx_series_stats_series_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_series_stats_series_id ON public.series_stats USING btree (series_id);


--
-- Name: idx_system_settings_key; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_system_settings_key ON public.system_settings USING btree (key);


--
-- Name: idx_teams_display_name; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_teams_display_name ON public.teams USING btree (display_name);


--
-- Name: idx_unique_user_date_availability; Type: INDEX; Schema: public; Owner: -
--

CREATE UNIQUE INDEX idx_unique_user_date_availability ON public.player_availability USING btree (user_id, match_date) WHERE (user_id IS NOT NULL);


--
-- Name: idx_upa_unique_player_check; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_upa_unique_player_check ON public.user_player_associations USING btree (tenniscores_player_id);


--
-- Name: idx_users_league_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_users_league_id ON public.users USING btree (league_id);


--
-- Name: idx_users_tenniscores_player_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_users_tenniscores_player_id ON public.users USING btree (tenniscores_player_id);


--
-- Name: player_availability trigger_auto_populate_player_id; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER trigger_auto_populate_player_id BEFORE INSERT ON public.player_availability FOR EACH ROW EXECUTE FUNCTION public.auto_populate_player_id();


--
-- Name: pickup_games trigger_pickup_games_updated_at; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER trigger_pickup_games_updated_at BEFORE UPDATE ON public.pickup_games FOR EACH ROW EXECUTE FUNCTION public.update_pickup_games_updated_at();


--
-- Name: player_season_tracking trigger_update_player_season_tracking_updated_at; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER trigger_update_player_season_tracking_updated_at BEFORE UPDATE ON public.player_season_tracking FOR EACH ROW EXECUTE FUNCTION public.update_player_season_tracking_updated_at();


--
-- Name: clubs update_clubs_updated_at; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER update_clubs_updated_at BEFORE UPDATE ON public.clubs FOR EACH ROW EXECUTE FUNCTION public.update_updated_at_column();


--
-- Name: leagues update_leagues_updated_at; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER update_leagues_updated_at BEFORE UPDATE ON public.leagues FOR EACH ROW EXECUTE FUNCTION public.update_updated_at_column();


--
-- Name: players update_players_updated_at; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER update_players_updated_at BEFORE UPDATE ON public.players FOR EACH ROW EXECUTE FUNCTION public.update_updated_at_column();


--
-- Name: series update_series_updated_at; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER update_series_updated_at BEFORE UPDATE ON public.series FOR EACH ROW EXECUTE FUNCTION public.update_updated_at_column();


--
-- Name: system_settings update_system_settings_updated_at; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER update_system_settings_updated_at BEFORE UPDATE ON public.system_settings FOR EACH ROW EXECUTE FUNCTION public.update_updated_at_column();


--
-- Name: teams update_teams_updated_at; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER update_teams_updated_at BEFORE UPDATE ON public.teams FOR EACH ROW EXECUTE FUNCTION public.update_teams_updated_at_column();


--
-- Name: activity_log activity_log_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.activity_log
    ADD CONSTRAINT activity_log_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(id);


--
-- Name: club_leagues club_leagues_club_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.club_leagues
    ADD CONSTRAINT club_leagues_club_id_fkey FOREIGN KEY (club_id) REFERENCES public.clubs(id);


--
-- Name: club_leagues club_leagues_league_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.club_leagues
    ADD CONSTRAINT club_leagues_league_id_fkey FOREIGN KEY (league_id) REFERENCES public.leagues(id);


--
-- Name: group_members fk_group_members_added_by_user; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.group_members
    ADD CONSTRAINT fk_group_members_added_by_user FOREIGN KEY (added_by_user_id) REFERENCES public.users(id);


--
-- Name: group_members fk_group_members_group; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.group_members
    ADD CONSTRAINT fk_group_members_group FOREIGN KEY (group_id) REFERENCES public.groups(id) ON DELETE CASCADE;


--
-- Name: group_members fk_group_members_user; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.group_members
    ADD CONSTRAINT fk_group_members_user FOREIGN KEY (user_id) REFERENCES public.users(id);


--
-- Name: groups fk_groups_creator_user; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.groups
    ADD CONSTRAINT fk_groups_creator_user FOREIGN KEY (creator_user_id) REFERENCES public.users(id);


--
-- Name: match_scores fk_match_scores_away_team_id; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.match_scores
    ADD CONSTRAINT fk_match_scores_away_team_id FOREIGN KEY (away_team_id) REFERENCES public.teams(id);


--
-- Name: match_scores fk_match_scores_home_team_id; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.match_scores
    ADD CONSTRAINT fk_match_scores_home_team_id FOREIGN KEY (home_team_id) REFERENCES public.teams(id);


--
-- Name: match_scores fk_match_scores_league_id; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.match_scores
    ADD CONSTRAINT fk_match_scores_league_id FOREIGN KEY (league_id) REFERENCES public.leagues(id);


--
-- Name: player_history fk_player_history_league_id; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.player_history
    ADD CONSTRAINT fk_player_history_league_id FOREIGN KEY (league_id) REFERENCES public.leagues(id);


--
-- Name: player_history fk_player_history_player_id; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.player_history
    ADD CONSTRAINT fk_player_history_player_id FOREIGN KEY (player_id) REFERENCES public.players(id);


--
-- Name: schedule fk_schedule_away_team_id; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.schedule
    ADD CONSTRAINT fk_schedule_away_team_id FOREIGN KEY (away_team_id) REFERENCES public.teams(id);


--
-- Name: schedule fk_schedule_home_team_id; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.schedule
    ADD CONSTRAINT fk_schedule_home_team_id FOREIGN KEY (home_team_id) REFERENCES public.teams(id);


--
-- Name: schedule fk_schedule_league_id; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.schedule
    ADD CONSTRAINT fk_schedule_league_id FOREIGN KEY (league_id) REFERENCES public.leagues(id);


--
-- Name: series_stats fk_series_stats_league_id; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.series_stats
    ADD CONSTRAINT fk_series_stats_league_id FOREIGN KEY (league_id) REFERENCES public.leagues(id);


--
-- Name: series_stats fk_series_stats_series_id; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.series_stats
    ADD CONSTRAINT fk_series_stats_series_id FOREIGN KEY (series_id) REFERENCES public.series(id);


--
-- Name: series_stats fk_series_stats_team_id; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.series_stats
    ADD CONSTRAINT fk_series_stats_team_id FOREIGN KEY (team_id) REFERENCES public.teams(id);


--
-- Name: user_player_associations fk_upa_user_id; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.user_player_associations
    ADD CONSTRAINT fk_upa_user_id FOREIGN KEY (user_id) REFERENCES public.users(id);


--
-- Name: user_instructions fk_user_instructions_team_id; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.user_instructions
    ADD CONSTRAINT fk_user_instructions_team_id FOREIGN KEY (team_id) REFERENCES public.teams(id);


--
-- Name: match_scores match_scores_away_team_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.match_scores
    ADD CONSTRAINT match_scores_away_team_id_fkey FOREIGN KEY (away_team_id) REFERENCES public.teams(id);


--
-- Name: match_scores match_scores_home_team_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.match_scores
    ADD CONSTRAINT match_scores_home_team_id_fkey FOREIGN KEY (home_team_id) REFERENCES public.teams(id);


--
-- Name: pickup_game_participants pickup_game_participants_pickup_game_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.pickup_game_participants
    ADD CONSTRAINT pickup_game_participants_pickup_game_id_fkey FOREIGN KEY (pickup_game_id) REFERENCES public.pickup_games(id) ON DELETE CASCADE;


--
-- Name: pickup_game_participants pickup_game_participants_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.pickup_game_participants
    ADD CONSTRAINT pickup_game_participants_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(id) ON DELETE CASCADE;


--
-- Name: pickup_games pickup_games_creator_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.pickup_games
    ADD CONSTRAINT pickup_games_creator_user_id_fkey FOREIGN KEY (creator_user_id) REFERENCES public.users(id) ON DELETE SET NULL;


--
-- Name: player_availability player_availability_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.player_availability
    ADD CONSTRAINT player_availability_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(id);


--
-- Name: players players_league_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.players
    ADD CONSTRAINT players_league_id_fkey FOREIGN KEY (league_id) REFERENCES public.leagues(id);


--
-- Name: players players_team_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.players
    ADD CONSTRAINT players_team_id_fkey FOREIGN KEY (team_id) REFERENCES public.teams(id);


--
-- Name: poll_choices poll_choices_poll_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.poll_choices
    ADD CONSTRAINT poll_choices_poll_id_fkey FOREIGN KEY (poll_id) REFERENCES public.polls(id) ON DELETE CASCADE;


--
-- Name: poll_responses poll_responses_choice_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.poll_responses
    ADD CONSTRAINT poll_responses_choice_id_fkey FOREIGN KEY (choice_id) REFERENCES public.poll_choices(id);


--
-- Name: poll_responses poll_responses_poll_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.poll_responses
    ADD CONSTRAINT poll_responses_poll_id_fkey FOREIGN KEY (poll_id) REFERENCES public.polls(id) ON DELETE CASCADE;


--
-- Name: polls polls_created_by_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.polls
    ADD CONSTRAINT polls_created_by_fkey FOREIGN KEY (created_by) REFERENCES public.users(id);


--
-- Name: pro_lessons pro_lessons_pro_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.pro_lessons
    ADD CONSTRAINT pro_lessons_pro_id_fkey FOREIGN KEY (pro_id) REFERENCES public.pros(id);


--
-- Name: schedule schedule_away_team_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.schedule
    ADD CONSTRAINT schedule_away_team_id_fkey FOREIGN KEY (away_team_id) REFERENCES public.teams(id);


--
-- Name: schedule schedule_home_team_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.schedule
    ADD CONSTRAINT schedule_home_team_id_fkey FOREIGN KEY (home_team_id) REFERENCES public.teams(id);


--
-- Name: series_leagues series_leagues_league_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.series_leagues
    ADD CONSTRAINT series_leagues_league_id_fkey FOREIGN KEY (league_id) REFERENCES public.leagues(id);


--
-- Name: series_leagues series_leagues_series_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.series_leagues
    ADD CONSTRAINT series_leagues_series_id_fkey FOREIGN KEY (series_id) REFERENCES public.series(id);


--
-- Name: series_stats series_stats_team_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.series_stats
    ADD CONSTRAINT series_stats_team_id_fkey FOREIGN KEY (team_id) REFERENCES public.teams(id);


--
-- Name: teams teams_club_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.teams
    ADD CONSTRAINT teams_club_id_fkey FOREIGN KEY (club_id) REFERENCES public.clubs(id);


--
-- Name: teams teams_league_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.teams
    ADD CONSTRAINT teams_league_id_fkey FOREIGN KEY (league_id) REFERENCES public.leagues(id);


--
-- Name: teams teams_series_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.teams
    ADD CONSTRAINT teams_series_id_fkey FOREIGN KEY (series_id) REFERENCES public.series(id);


--
-- Name: user_instructions user_instructions_series_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.user_instructions
    ADD CONSTRAINT user_instructions_series_id_fkey FOREIGN KEY (series_id) REFERENCES public.series(id);


--
-- Name: players users_club_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.players
    ADD CONSTRAINT users_club_id_fkey FOREIGN KEY (club_id) REFERENCES public.clubs(id);


--
-- Name: players users_series_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.players
    ADD CONSTRAINT users_series_id_fkey FOREIGN KEY (series_id) REFERENCES public.series(id);


--
-- PostgreSQL database dump complete
--

