--
-- PostgreSQL database dump
--

-- Dumped from database version 15.13 (Homebrew)
-- Dumped by pg_dump version 15.13 (Homebrew)

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

SET default_tablespace = '';

SET default_table_access_method = heap;

--
-- Name: alembic_version; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.alembic_version (
    version_num character varying(32) NOT NULL
);


ALTER TABLE public.alembic_version OWNER TO postgres;

--
-- Name: clubs; Type: TABLE; Schema: public; Owner: rossfreedman
--

CREATE TABLE public.clubs (
    id integer NOT NULL,
    name character varying(255) NOT NULL
);


ALTER TABLE public.clubs OWNER TO rossfreedman;

--
-- Name: clubs_id_seq; Type: SEQUENCE; Schema: public; Owner: rossfreedman
--

CREATE SEQUENCE public.clubs_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.clubs_id_seq OWNER TO rossfreedman;

--
-- Name: clubs_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: rossfreedman
--

ALTER SEQUENCE public.clubs_id_seq OWNED BY public.clubs.id;


--
-- Name: player_availability; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.player_availability (
    id integer NOT NULL,
    player_name character varying(255) NOT NULL,
    match_date date NOT NULL,
    availability_status integer DEFAULT 3 NOT NULL,
    updated_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP,
    series_id integer NOT NULL,
    CONSTRAINT valid_availability_status CHECK ((availability_status = ANY (ARRAY[1, 2, 3])))
);


ALTER TABLE public.player_availability OWNER TO postgres;

--
-- Name: player_availability_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.player_availability_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.player_availability_id_seq OWNER TO postgres;

--
-- Name: player_availability_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.player_availability_id_seq OWNED BY public.player_availability.id;


--
-- Name: series; Type: TABLE; Schema: public; Owner: rossfreedman
--

CREATE TABLE public.series (
    id integer NOT NULL,
    name character varying(255) NOT NULL
);


ALTER TABLE public.series OWNER TO rossfreedman;

--
-- Name: series_id_seq; Type: SEQUENCE; Schema: public; Owner: rossfreedman
--

CREATE SEQUENCE public.series_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.series_id_seq OWNER TO rossfreedman;

--
-- Name: series_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: rossfreedman
--

ALTER SEQUENCE public.series_id_seq OWNED BY public.series.id;


--
-- Name: user_activity_logs; Type: TABLE; Schema: public; Owner: rossfreedman
--

CREATE TABLE public.user_activity_logs (
    id integer NOT NULL,
    user_email character varying(255) NOT NULL,
    activity_type character varying(255) NOT NULL,
    page character varying(255),
    action text,
    details text,
    ip_address character varying(45),
    "timestamp" timestamp without time zone DEFAULT CURRENT_TIMESTAMP
);


ALTER TABLE public.user_activity_logs OWNER TO rossfreedman;

--
-- Name: user_activity_logs_id_seq; Type: SEQUENCE; Schema: public; Owner: rossfreedman
--

CREATE SEQUENCE public.user_activity_logs_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.user_activity_logs_id_seq OWNER TO rossfreedman;

--
-- Name: user_activity_logs_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: rossfreedman
--

ALTER SEQUENCE public.user_activity_logs_id_seq OWNED BY public.user_activity_logs.id;


--
-- Name: user_instructions; Type: TABLE; Schema: public; Owner: rossfreedman
--

CREATE TABLE public.user_instructions (
    id integer NOT NULL,
    user_email character varying(255) NOT NULL,
    instruction text NOT NULL,
    team_id integer,
    created_at timestamp without time zone,
    is_active boolean DEFAULT true NOT NULL
);


ALTER TABLE public.user_instructions OWNER TO rossfreedman;

--
-- Name: user_instructions_id_seq; Type: SEQUENCE; Schema: public; Owner: rossfreedman
--

CREATE SEQUENCE public.user_instructions_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.user_instructions_id_seq OWNER TO rossfreedman;

--
-- Name: user_instructions_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: rossfreedman
--

ALTER SEQUENCE public.user_instructions_id_seq OWNED BY public.user_instructions.id;


--
-- Name: users; Type: TABLE; Schema: public; Owner: rossfreedman
--

CREATE TABLE public.users (
    id integer NOT NULL,
    email character varying(255) NOT NULL,
    password_hash character varying(255) NOT NULL,
    first_name character varying(255) NOT NULL,
    last_name character varying(255) NOT NULL,
    club_id integer,
    series_id integer,
    club_automation_password character varying(255),
    created_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP,
    last_login timestamp without time zone,
    is_admin boolean DEFAULT false NOT NULL
);


ALTER TABLE public.users OWNER TO rossfreedman;

--
-- Name: users_id_seq; Type: SEQUENCE; Schema: public; Owner: rossfreedman
--

CREATE SEQUENCE public.users_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.users_id_seq OWNER TO rossfreedman;

--
-- Name: users_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: rossfreedman
--

ALTER SEQUENCE public.users_id_seq OWNED BY public.users.id;


--
-- Name: clubs id; Type: DEFAULT; Schema: public; Owner: rossfreedman
--

ALTER TABLE ONLY public.clubs ALTER COLUMN id SET DEFAULT nextval('public.clubs_id_seq'::regclass);


--
-- Name: player_availability id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.player_availability ALTER COLUMN id SET DEFAULT nextval('public.player_availability_id_seq'::regclass);


--
-- Name: series id; Type: DEFAULT; Schema: public; Owner: rossfreedman
--

ALTER TABLE ONLY public.series ALTER COLUMN id SET DEFAULT nextval('public.series_id_seq'::regclass);


--
-- Name: user_activity_logs id; Type: DEFAULT; Schema: public; Owner: rossfreedman
--

ALTER TABLE ONLY public.user_activity_logs ALTER COLUMN id SET DEFAULT nextval('public.user_activity_logs_id_seq'::regclass);


--
-- Name: user_instructions id; Type: DEFAULT; Schema: public; Owner: rossfreedman
--

ALTER TABLE ONLY public.user_instructions ALTER COLUMN id SET DEFAULT nextval('public.user_instructions_id_seq'::regclass);


--
-- Name: users id; Type: DEFAULT; Schema: public; Owner: rossfreedman
--

ALTER TABLE ONLY public.users ALTER COLUMN id SET DEFAULT nextval('public.users_id_seq'::regclass);


--
-- Name: alembic_version alembic_version_pkc; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.alembic_version
    ADD CONSTRAINT alembic_version_pkc PRIMARY KEY (version_num);


--
-- Name: clubs clubs_name_key; Type: CONSTRAINT; Schema: public; Owner: rossfreedman
--

ALTER TABLE ONLY public.clubs
    ADD CONSTRAINT clubs_name_key UNIQUE (name);


--
-- Name: clubs clubs_pkey; Type: CONSTRAINT; Schema: public; Owner: rossfreedman
--

ALTER TABLE ONLY public.clubs
    ADD CONSTRAINT clubs_pkey PRIMARY KEY (id);


--
-- Name: player_availability player_availability_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.player_availability
    ADD CONSTRAINT player_availability_pkey PRIMARY KEY (id);


--
-- Name: series series_name_key; Type: CONSTRAINT; Schema: public; Owner: rossfreedman
--

ALTER TABLE ONLY public.series
    ADD CONSTRAINT series_name_key UNIQUE (name);


--
-- Name: series series_pkey; Type: CONSTRAINT; Schema: public; Owner: rossfreedman
--

ALTER TABLE ONLY public.series
    ADD CONSTRAINT series_pkey PRIMARY KEY (id);


--
-- Name: user_activity_logs user_activity_logs_pkey; Type: CONSTRAINT; Schema: public; Owner: rossfreedman
--

ALTER TABLE ONLY public.user_activity_logs
    ADD CONSTRAINT user_activity_logs_pkey PRIMARY KEY (id);


--
-- Name: user_instructions user_instructions_pkey; Type: CONSTRAINT; Schema: public; Owner: rossfreedman
--

ALTER TABLE ONLY public.user_instructions
    ADD CONSTRAINT user_instructions_pkey PRIMARY KEY (id);


--
-- Name: users users_email_key; Type: CONSTRAINT; Schema: public; Owner: rossfreedman
--

ALTER TABLE ONLY public.users
    ADD CONSTRAINT users_email_key UNIQUE (email);


--
-- Name: users users_pkey; Type: CONSTRAINT; Schema: public; Owner: rossfreedman
--

ALTER TABLE ONLY public.users
    ADD CONSTRAINT users_pkey PRIMARY KEY (id);


--
-- Name: player_availability player_availability_series_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.player_availability
    ADD CONSTRAINT player_availability_series_id_fkey FOREIGN KEY (series_id) REFERENCES public.series(id);


--
-- Name: users users_club_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: rossfreedman
--

ALTER TABLE ONLY public.users
    ADD CONSTRAINT users_club_id_fkey FOREIGN KEY (club_id) REFERENCES public.clubs(id);


--
-- Name: users users_series_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: rossfreedman
--

ALTER TABLE ONLY public.users
    ADD CONSTRAINT users_series_id_fkey FOREIGN KEY (series_id) REFERENCES public.series(id);


--
-- PostgreSQL database dump complete
--

