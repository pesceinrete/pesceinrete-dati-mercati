<?php
/**
 * Plugin Name: Pesceinrete — Dati e mercati
 * Description: Sezione di dati di mercato ittici: prezzi settimanali all'importazione, posizione stagionale, importazioni italiane. Crea da sola le pagine e legge i dati dal repository.
 * Version: 1.1.0
 * Author: Pesceinrete
 * Text Domain: pesceinrete-dati-mercati
 *
 * Installazione: Plugin → Aggiungi nuovo → Carica plugin → questo zip → Attiva.
 * All'attivazione crea le pagine /dati-mercati/ e /market-data/ con una
 * pagina figlia per specie, come pagine PRIVATE: le vedono solo gli
 * amministratori, dentro il sito vero, con il tema vero. Quando l'aspetto
 * convince, un pulsante in Impostazioni → Dati e mercati le pubblica.
 * Nella stessa schermata si indica l'indirizzo dei file pubblicati dal
 * repository (GitHub Pages); senza, il plugin usa la copia inclusa.
 *
 * @package Pesceinrete
 */

defined( 'ABSPATH' ) || exit;

define( 'PIR_DM_VERSIONE', '1.1.0' );
define( 'PIR_DM_CARTELLA', plugin_dir_path( __FILE__ ) . 'assets/' );
define( 'PIR_DM_INDIRIZZO', plugin_dir_url( __FILE__ ) . 'assets/' );
define( 'PIR_DM_OPZIONE', 'pir_dm_url_base' );
define( 'PIR_DM_OPZIONE_ISCRIZIONE', 'pir_dm_url_iscrizione' );

const PIR_DM_SPECIE = array(
	'salmone'     => array( 'Salmone', 'Salmon' ),
	'orata'       => array( 'Orata', 'Sea bream' ),
	'spigola'     => array( 'Spigola', 'Sea bass' ),
	'gambero'     => array( 'Gambero', 'Shrimp' ),
	'polpo'       => array( 'Polpo', 'Octopus' ),
	'calamaro'    => array( 'Calamaro', 'Squid' ),
	'seppia'      => array( 'Seppia', 'Cuttlefish' ),
	'astice'      => array( 'Astice', 'Lobster' ),
	'pesce_spada' => array( 'Pesce spada', 'Swordfish' ),
);

/* --------------------------------------------------------------------------
 * Origine dei file: repository (GitHub Pages) oppure copia inclusa
 * -------------------------------------------------------------------------- */

function pir_dm_url_base() {
	$base = trim( (string) get_option( PIR_DM_OPZIONE, '' ) );
	return $base ? trailingslashit( $base ) : '';
}

/**
 * Contenuto di un file.
 *
 * Regola di sicurezza: il CODICE (le pagine HTML con il loro script) viene
 * sempre dalla copia inclusa nel plugin e cambia solo aggiornando il
 * plugin. Dal repository arrivano soltanto i DATI: JSON, blocchi di
 * sintesi, immagini. Così un eventuale accesso abusivo al repository non
 * può far eseguire script sul sito. I dati remoti hanno una cache di
 * un'ora; se il repository non risponde si usa la copia inclusa, e la
 * pagina non resta mai vuota.
 */
function pir_dm_e_dato( $relativo ) {
	return (bool) preg_match( '#^data/.+\.(json|html|png)$#', $relativo );
}

function pir_dm_file( $relativo ) {
	$base = pir_dm_url_base();
	if ( $base && pir_dm_e_dato( $relativo ) ) {
		$chiave  = 'pir_dm_' . md5( $relativo );
		$incache = get_transient( $chiave );
		if ( false !== $incache ) {
			return $incache;
		}
		$risposta = wp_remote_get( $base . $relativo, array( 'timeout' => 8 ) );
		if ( ! is_wp_error( $risposta ) && 200 === wp_remote_retrieve_response_code( $risposta ) ) {
			$corpo = wp_remote_retrieve_body( $risposta );
			// un blocco di sintesi remoto non deve portare script
			if ( $corpo && preg_match( '#\.html$#', $relativo ) ) {
				$corpo = preg_replace( '#<script\b[^>]*>.*?</script>#is', '', $corpo );
				$corpo = preg_replace( '#\son[a-z]+\s*=\s*("[^"]*"|\'[^\']*\')#i', '', $corpo );
			}
			if ( $corpo ) {
				set_transient( $chiave, $corpo, HOUR_IN_SECONDS );
				return $corpo;
			}
		}
	}
	$locale = PIR_DM_CARTELLA . $relativo;
	return file_exists( $locale ) ? file_get_contents( $locale ) : ''; // phpcs:ignore WordPress.WP.AlternativeFunctions
}

/** Indirizzo pubblico del file dei dati, letto dal browser. */
function pir_dm_url_dati( $lingua ) {
	$nome = 'data/mercati' . ( 'en' === $lingua ? '.en' : '' ) . '.json';
	$base = pir_dm_url_base();
	if ( $base ) {
		return $base . $nome . '?v=' . gmdate( 'YmdH' );
	}
	$percorso = PIR_DM_CARTELLA . $nome;
	$versione = file_exists( $percorso ) ? (string) filemtime( $percorso ) : (string) time();
	return PIR_DM_INDIRIZZO . $nome . '?v=' . $versione;
}

/* --------------------------------------------------------------------------
 * Shortcode
 * -------------------------------------------------------------------------- */

function pir_dm_shortcode( $attributi = array() ) {
	$attributi = shortcode_atts(
		array( 'prodotto' => 'salmone', 'lingua' => 'it' ),
		$attributi,
		'dati_mercati'
	);
	$lingua   = ( 'en' === $attributi['lingua'] ) ? 'en' : 'it';
	$suffisso = ( 'en' === $lingua ) ? '.en' : '';
	$prodotto = sanitize_key( $attributi['prodotto'] );

	$html = pir_dm_file( 'dati-mercati' . $suffisso . '.html' );
	if ( ! $html ) {
		return '<p>Sezione dati non disponibile. Contattare la redazione.</p>';
	}
	// Lo stile della pagina sta nell'<head>: va conservato prima di tenere solo il <body>.
	$stile = '';
	if ( preg_match( '#<style\b[^>]*>.*?</style>#si', $html, $blocco ) ) {
		$stile = $blocco[0];
	}
	if ( preg_match( '#<body[^>]*>(.*)</body>#si', $html, $parti ) ) {
		$html = $stile . $parti[1];
	}
	// La testata (briciole, titolo, occhiello) serve solo all'anteprima:
	// dentro il sito titolo e menu li mette il tema.
	// Al posto della testata dell'anteprima va il titolo della pagina WordPress,
	// come unico h1, dentro lo sfondo della sezione. post_title evita il
	// prefisso "Privato:" che WordPress aggiunge alle pagine private.
	$titolo_h1 = esc_html( get_post_field( 'post_title', get_the_ID() ) );
	$html      = preg_replace(
		'#<header class="pir-testata"[^>]*>.*?</header>#si',
		'<h1 class="pir-titolo-sezione pir-titolo-pagina">' . $titolo_h1 . '</h1>',
		$html,
		1
	);
	// Il logo nella testatina della sezione serve fuori dal sito: dentro, il
	// logo lo mostra già l'intestazione del tema e ripeterlo sarebbe di troppo.
	$html = preg_replace( '#<a [^>]*data-solo-anteprima[^>]*>.*?</a>#si', '', $html );
	// Il logo nella testatina della sezione serve fuori dal sito: dentro, il
	// logo lo mostra già l'intestazione del tema e ripeterlo sarebbe di troppo.
	$html = preg_replace( '#<a [^>]*data-solo-anteprima[^>]*>.*?</a>#si', '', $html );

	// Blocco statico della specie: testo vero, indicizzabile, inserito dal server.
	$sintesi = pir_dm_file( 'data/sintesi-' . $prodotto . $suffisso . '.html' );
	if ( $sintesi ) {
		$html = str_replace(
			'<div id="pir-sintesi-statica"></div>',
			'<div id="pir-sintesi-statica">' . $sintesi . '</div>',
			$html
		);
	}

	$radice = ( 'en' === $lingua ) ? 'market-data' : 'dati-mercati';
	$avvio  = 'window.PESCEINRETE_URL_DATI=' . wp_json_encode( pir_dm_url_dati( $lingua ) ) . ';';
	$iscrizione = trim( (string) get_option( PIR_DM_OPZIONE_ISCRIZIONE, '' ) );
	if ( $iscrizione ) {
		$avvio .= 'window.PESCEINRETE_URL_ISCRIZIONE=' . wp_json_encode( esc_url_raw( $iscrizione ) ) . ';';
	}
	$avvio .= 'window.PESCEINRETE_PRODOTTO=' . wp_json_encode( $prodotto ) . ';';
	$avvio .= 'window.PESCEINRETE_URL_PRODOTTO=' . wp_json_encode( home_url( '/' . $radice . '/{id}/' ) ) . ';';
	// Gli indirizzi veri delle pagine delle specie: la pagina usa questi.
	$mappa   = pir_dm_mappa_pagine();
	$pagine  = isset( $mappa[ $lingua ] ) ? $mappa[ $lingua ] : array();
	unset( $pagine[''] );
	$avvio .= 'window.PESCEINRETE_URL_PRODOTTI=' . wp_json_encode( (object) $pagine ) . ';';
	return '<script>' . $avvio . '</script>' . $html;
}
add_shortcode( 'dati_mercati', 'pir_dm_shortcode' );

/* --------------------------------------------------------------------------
 * Pagine: create all'attivazione, una per specie, nelle due lingue
 * -------------------------------------------------------------------------- */

function pir_dm_crea_pagine() {
	// Le pagine che esistono già, ovunque siano e in qualunque stato: una
	// specie che ha già la sua pagina non ne riceve una seconda.
	global $wpdb;
	$presenti = array();
	$pagine   = $wpdb->get_results(
		"SELECT post_content FROM {$wpdb->posts}
		 WHERE post_type = 'page' AND post_status IN ('publish','private','draft','pending','future')
		 AND post_content LIKE '%[dati_mercati%'"
	);
	foreach ( (array) $pagine as $pagina ) {
		if ( preg_match( '/\[dati_mercati\b([^\]]*)\]/', $pagina->post_content, $trovato ) ) {
			$attributi = shortcode_parse_atts( $trovato[1] );
			$attributi = is_array( $attributi ) ? $attributi : array();
			$lingua_p  = ( isset( $attributi['lingua'] ) && 'en' === $attributi['lingua'] ) ? 'en' : 'it';
			$presenti[ $lingua_p . '|' . ( isset( $attributi['prodotto'] ) ? sanitize_key( $attributi['prodotto'] ) : '' ) ] = true;
		}
	}
	foreach ( array( 'it' => 'dati-mercati', 'en' => 'market-data' ) as $lingua => $slug ) {
		$titolo = ( 'en' === $lingua ) ? 'Market data' : 'Dati e mercati';
		$padre  = pir_dm_assicura_pagina( $slug, $titolo, '[dati_mercati lingua="' . $lingua . '"]', 0 );
		if ( ! $padre || is_wp_error( $padre ) ) {
			continue;   // senza pagina d'ingresso non si creano pagine orfane
		}
		foreach ( PIR_DM_SPECIE as $id => $nomi ) {
			if ( isset( $presenti[ $lingua . '|' . $id ] ) ) {
				continue;
			}
			$nome = ( 'en' === $lingua ) ? $nomi[1] : $nomi[0];
			pir_dm_assicura_pagina(
				$id,
				$nome,
				'[dati_mercati prodotto="' . $id . '" lingua="' . $lingua . '"]',
				$padre
			);
		}
	}
	delete_transient( 'pir_dm_pagine' );
	flush_rewrite_rules();
}
register_activation_hook( __FILE__, 'pir_dm_crea_pagine' );

/**
 * Aggiornamento del plugin: se l'elenco delle specie è cambiato, crea le
 * pagine che mancano senza bisogno di disattivare e riattivare. Le pagine
 * delle specie non più pubblicate non vengono toccate: si cestinano a mano.
 */
function pir_dm_aggiorna_pagine() {
	if ( get_option( 'pir_dm_versione' ) !== PIR_DM_VERSIONE ) {
		pir_dm_crea_pagine();
		update_option( 'pir_dm_versione', PIR_DM_VERSIONE );
	}
}
add_action( 'admin_init', 'pir_dm_aggiorna_pagine' );

function pir_dm_assicura_pagina( $slug, $titolo, $contenuto, $padre ) {
	$esistente = get_posts(
		array(
			'name'        => $slug,
			'post_type'   => 'page',
			'post_parent' => $padre,
			'post_status' => array( 'publish', 'draft', 'private' ),
			'numberposts' => 1,
		)
	);
	if ( $esistente ) {
		return $esistente[0]->ID;
	}
	return wp_insert_post(
		array(
			'post_title'   => $titolo,
			'post_name'    => $slug,
			'post_content' => $contenuto,
			'post_status'  => 'private',   // visibili solo agli amministratori finché non si pubblicano
			'post_type'    => 'page',
			'post_parent'  => $padre,
			'page_template' => 'default',
		)
	);
}

/* --------------------------------------------------------------------------
 * Titolo, descrizione, hreflang e data di modifica
 * -------------------------------------------------------------------------- */

/**
 * Attributi dello shortcode [dati_mercati ...] nel contenuto della pagina
 * corrente, oppure null. Permette di riconoscere una pagina della sezione
 * anche se è stata creata o spostata a mano, fuori da /dati-mercati/.
 */
function pir_dm_attributi_pagina() {
	$post = get_queried_object();
	if ( ! $post || empty( $post->post_content ) || ! is_singular() ) {
		return null;
	}
	if ( ! preg_match( '/\[dati_mercati\b([^\]]*)\]/', $post->post_content, $trovato ) ) {
		return null;
	}
	$attributi = shortcode_parse_atts( $trovato[1] );
	return is_array( $attributi ) ? $attributi : array();
}

function pir_dm_e_pagina_sezione() {
	$post = get_queried_object();
	if ( ! $post || ! isset( $post->post_name ) ) {
		return false;
	}
	if ( null !== pir_dm_attributi_pagina() ) {
		return true;
	}
	if ( in_array( $post->post_name, array( 'dati-mercati', 'market-data' ), true ) ) {
		return true;
	}
	if ( empty( $post->post_parent ) ) {
		return false;
	}
	return in_array( get_post_field( 'post_name', $post->post_parent ), array( 'dati-mercati', 'market-data' ), true );
}

function pir_dm_lingua_pagina() {
	$post = get_queried_object();
	if ( ! $post ) {
		return 'it';
	}
	$attributi = pir_dm_attributi_pagina();
	if ( $attributi && ! empty( $attributi['lingua'] ) ) {
		return ( 'en' === $attributi['lingua'] ) ? 'en' : 'it';
	}
	$slug  = $post->post_name;
	$padre = ! empty( $post->post_parent ) ? get_post_field( 'post_name', $post->post_parent ) : '';
	return ( 'market-data' === $slug || 'market-data' === $padre ) ? 'en' : 'it';
}

function pir_dm_indice( $lingua ) {
	static $cache = array();
	if ( ! isset( $cache[ $lingua ] ) ) {
		$testo            = pir_dm_file( 'data/mercati' . ( 'en' === $lingua ? '.en' : '' ) . '.json' );
		$cache[ $lingua ] = $testo ? json_decode( $testo, true ) : false;
	}
	return $cache[ $lingua ];
}

function pir_dm_voce_pagina() {
	$dati = pir_dm_indice( pir_dm_lingua_pagina() );
	if ( ! $dati || empty( $dati['prodotti'] ) ) {
		return null;
	}
	$slug      = get_post_field( 'post_name', get_queried_object_id() );
	$attributi = pir_dm_attributi_pagina();
	if ( $attributi && ! empty( $attributi['prodotto'] ) ) {
		$slug = sanitize_key( $attributi['prodotto'] );
	}
	foreach ( $dati['prodotti'] as $voce ) {
		if ( $voce['id'] === $slug ) {
			return $voce;
		}
	}
	// Pagina d'ingresso della sezione: titolo e descrizione sono della
	// sezione, non della prima specie. L'immagine resta quella della prima.
	$inglese = ( 'en' === pir_dm_lingua_pagina() );
	return array(
		'id'                 => $dati['prodotti'][0]['id'],
		'titolo_pagina'      => $inglese
			? 'Seafood market data: weekly import prices and volumes in Italy'
			: 'Dati e mercati ittici: prezzi settimanali all\'importazione e arrivi in Italia',
		'descrizione_pagina' => $inglese
			? 'Weekly prices for salmon, sea bream, sea bass, shrimp, octopus, squid, cuttlefish, lobster and swordfish, with volumes, origins and Italian imports. Official sources, updated every week.'
			: 'Prezzi settimanali di salmone, orata, spigola, gambero, polpo, calamaro, seppia, astice e pesce spada, con volumi, provenienze e importazioni italiane. Fonti ufficiali, aggiornamento ogni settimana.',
	);
}

/**
 * Dove stanno davvero le pagine della sezione: lingua => specie => indirizzo.
 * La specie '' è la pagina d'ingresso. Si leggono le pagine che contengono
 * lo shortcode, ovunque siano: sotto /dati-mercati/ oppure alla radice del
 * sito. I collegamenti fra le specie usano questi indirizzi, non uno schema
 * fisso. Le pagine private compaiono solo a chi può vederle.
 */
function pir_dm_mappa_pagine( $solo_pubbliche = false ) {
	global $wpdb;
	static $righe = null;
	if ( null === $righe ) {
		$righe = get_transient( 'pir_dm_pagine' );
		if ( ! is_array( $righe ) ) {
			$righe  = array();
			$pagine = $wpdb->get_results(
				"SELECT ID, post_status, post_content FROM {$wpdb->posts}
				 WHERE post_type = 'page' AND post_status IN ('publish','private')
				 AND post_content LIKE '%[dati_mercati%' ORDER BY ID"
			);
			foreach ( (array) $pagine as $pagina ) {
				if ( ! preg_match( '/\[dati_mercati\b([^\]]*)\]/', $pagina->post_content, $trovato ) ) {
					continue;
				}
				$attributi = shortcode_parse_atts( $trovato[1] );
				$attributi = is_array( $attributi ) ? $attributi : array();
				$righe[]   = array(
					'lingua'   => ( isset( $attributi['lingua'] ) && 'en' === $attributi['lingua'] ) ? 'en' : 'it',
					'prodotto' => isset( $attributi['prodotto'] ) ? sanitize_key( $attributi['prodotto'] ) : '',
					'pubblica' => ( 'publish' === $pagina->post_status ),
					'url'      => get_permalink( $pagina->ID ),
				);
			}
			set_transient( 'pir_dm_pagine', $righe, 10 * MINUTE_IN_SECONDS );
		}
	}
	$vede_private = ! $solo_pubbliche && current_user_can( 'read_private_pages' );
	$mappa        = array( 'it' => array(), 'en' => array() );
	foreach ( $righe as $riga ) {
		if ( ! $riga['pubblica'] && ! $vede_private ) {
			continue;
		}
		// a parità di specie vince la pagina pubblicata
		if ( ! isset( $mappa[ $riga['lingua'] ][ $riga['prodotto'] ] ) || $riga['pubblica'] ) {
			$mappa[ $riga['lingua'] ][ $riga['prodotto'] ] = $riga['url'];
		}
	}
	return $mappa;
}

function pir_dm_svuota_mappa_pagine() {
	delete_transient( 'pir_dm_pagine' );
}
add_action( 'save_post_page', 'pir_dm_svuota_mappa_pagine' );
add_action( 'deleted_post', 'pir_dm_svuota_mappa_pagine' );
add_action( 'trashed_post', 'pir_dm_svuota_mappa_pagine' );

function pir_dm_titolo( $titolo ) {
	if ( ! pir_dm_e_pagina_sezione() ) {
		return $titolo;
	}
	$voce = pir_dm_voce_pagina();
	return ( $voce && ! empty( $voce['titolo_pagina'] ) ) ? $voce['titolo_pagina'] . ' — Pesceinrete' : $titolo;
}
add_filter( 'pre_get_document_title', 'pir_dm_titolo' );

function pir_dm_testa() {
	if ( ! pir_dm_e_pagina_sezione() ) {
		return;
	}
	$voce = pir_dm_voce_pagina();
	if ( $voce && ! empty( $voce['descrizione_pagina'] ) ) {
		printf( '<meta name="description" content="%s">' . "\n", esc_attr( $voce['descrizione_pagina'] ) );
	}
	$slug = get_post_field( 'post_name', get_queried_object_id() );
	$figlia = in_array( $slug, array( 'dati-mercati', 'market-data' ), true ) ? '' : $slug . '/';

	// Anteprima per la condivisione: la card con il prezzo della settimana.
	$lingua  = pir_dm_lingua_pagina();
	$specie  = ( $voce && ! empty( $voce['id'] ) ) ? $voce['id'] : 'salmone';
	$suffix  = ( 'en' === $lingua ) ? '.en' : '';
	$img     = pir_dm_url_base() ? pir_dm_url_base() . 'data/social/' . $specie . $suffix . '.png' : PIR_DM_INDIRIZZO . 'data/social/' . $specie . $suffix . '.png';
	$titolo  = ( $voce && ! empty( $voce['titolo_pagina'] ) ) ? $voce['titolo_pagina'] : 'Dati e mercati';
	$descr   = ( $voce && ! empty( $voce['descrizione_pagina'] ) ) ? $voce['descrizione_pagina'] : '';
	printf( '<meta property="og:type" content="article">' . "\n" );
	printf( '<meta property="og:title" content="%s">' . "\n", esc_attr( $titolo ) );
	printf( '<meta property="og:description" content="%s">' . "\n", esc_attr( $descr ) );
	printf( '<meta property="og:image" content="%s?v=%s">' . "\n", esc_url( $img ), esc_attr( gmdate( 'YmdH' ) ) );
	printf( '<meta property="og:image:width" content="1200"><meta property="og:image:height" content="630">' . "\n" );
	printf( '<meta name="twitter:card" content="summary_large_image">' . "\n" );
	// hreflang: solo verso pagine che esistono e sono pubblicate.
	$attributi = pir_dm_attributi_pagina();
	$chiave    = ( $attributi && ! empty( $attributi['prodotto'] ) ) ? sanitize_key( $attributi['prodotto'] ) : '';
	$pubbliche = pir_dm_mappa_pagine( true );
	if ( isset( $pubbliche['it'][ $chiave ], $pubbliche['en'][ $chiave ] ) ) {
		printf( '<link rel="alternate" hreflang="it" href="%s">' . "\n", esc_url( $pubbliche['it'][ $chiave ] ) );
		printf( '<link rel="alternate" hreflang="en" href="%s">' . "\n", esc_url( $pubbliche['en'][ $chiave ] ) );
		printf( '<link rel="alternate" hreflang="x-default" href="%s">' . "\n", esc_url( $pubbliche['it'][ $chiave ] ) );
	}
}
add_action( 'wp_head', 'pir_dm_testa', 1 );

/* --------------------------------------------------------------------------
 * Convivenza con i plugin SEO
 *
 * Un plugin SEO scrive i propri titolo, descrizione e anteprima social e
 * copre quelli della sezione. Qui si passano i valori giusti ai plugin
 * più diffusi (Yoast, Rank Math, SEOPress, All in One SEO) attraverso i
 * loro filtri. Sulle pagine fuori dalla sezione non cambia niente.
 * -------------------------------------------------------------------------- */

function pir_dm_seo_titolo( $valore ) {
	if ( ! pir_dm_e_pagina_sezione() ) {
		return $valore;
	}
	$voce = pir_dm_voce_pagina();
	return ( $voce && ! empty( $voce['titolo_pagina'] ) ) ? $voce['titolo_pagina'] . ' — Pesceinrete' : $valore;
}

function pir_dm_seo_titolo_social( $valore ) {
	if ( ! pir_dm_e_pagina_sezione() ) {
		return $valore;
	}
	$voce = pir_dm_voce_pagina();
	return ( $voce && ! empty( $voce['titolo_pagina'] ) ) ? $voce['titolo_pagina'] : $valore;
}

function pir_dm_seo_descrizione( $valore ) {
	if ( ! pir_dm_e_pagina_sezione() ) {
		return $valore;
	}
	$voce = pir_dm_voce_pagina();
	return ( $voce && ! empty( $voce['descrizione_pagina'] ) ) ? $voce['descrizione_pagina'] : $valore;
}

function pir_dm_seo_immagine( $valore ) {
	if ( ! pir_dm_e_pagina_sezione() ) {
		return $valore;
	}
	$voce   = pir_dm_voce_pagina();
	$specie = ( $voce && ! empty( $voce['id'] ) ) ? $voce['id'] : 'salmone';
	$suffix = ( 'en' === pir_dm_lingua_pagina() ) ? '.en' : '';
	$base   = pir_dm_url_base() ? pir_dm_url_base() : PIR_DM_INDIRIZZO;
	return $base . 'data/social/' . $specie . $suffix . '.png';
}

foreach ( array( 'wpseo_title', 'rank_math/frontend/title', 'seopress_titles_title', 'aioseo_title' ) as $pir_dm_filtro ) {
	add_filter( $pir_dm_filtro, 'pir_dm_seo_titolo', 99 );
}
foreach ( array( 'wpseo_opengraph_title', 'wpseo_twitter_title', 'rank_math/opengraph/facebook/og_title', 'rank_math/opengraph/twitter/title', 'seopress_social_og_title', 'aioseo_facebook_tags_title' ) as $pir_dm_filtro ) {
	add_filter( $pir_dm_filtro, 'pir_dm_seo_titolo_social', 99 );
}
foreach ( array( 'wpseo_metadesc', 'wpseo_opengraph_desc', 'wpseo_twitter_description', 'rank_math/frontend/description', 'rank_math/opengraph/facebook/og_description', 'rank_math/opengraph/twitter/description', 'seopress_titles_desc', 'seopress_social_og_desc', 'aioseo_description' ) as $pir_dm_filtro ) {
	add_filter( $pir_dm_filtro, 'pir_dm_seo_descrizione', 99 );
}
foreach ( array( 'wpseo_opengraph_image', 'wpseo_twitter_image', 'rank_math/opengraph/facebook/image', 'rank_math/opengraph/twitter/image', 'seopress_social_og_thumb' ) as $pir_dm_filtro ) {
	add_filter( $pir_dm_filtro, 'pir_dm_seo_immagine', 99 );
}
unset( $pir_dm_filtro );

function pir_dm_data_modifica( $data, $formato, $post ) {
	if ( ! $post || ! pir_dm_e_pagina_sezione() ) {
		return $data;
	}
	$dati = pir_dm_indice( pir_dm_lingua_pagina() );
	if ( $dati && ! empty( $dati['generato_il'] ) ) {
		$momento = strtotime( $dati['generato_il'] );
		if ( $momento ) {
			return date_i18n( $formato, $momento );
		}
	}
	return $data;
}
add_filter( 'get_the_modified_date', 'pir_dm_data_modifica', 10, 3 );

/* --------------------------------------------------------------------------
 * Impostazioni: un campo solo
 * -------------------------------------------------------------------------- */

function pir_dm_menu() {
	add_options_page(
		'Dati e mercati',
		'Dati e mercati',
		'manage_options',
		'pir-dati-mercati',
		'pir_dm_pagina_opzioni'
	);
}
add_action( 'admin_menu', 'pir_dm_menu' );

function pir_dm_registra_opzioni() {
	register_setting(
		'pir_dm',
		PIR_DM_OPZIONE,
		array( 'sanitize_callback' => 'esc_url_raw' )
	);
	register_setting(
		'pir_dm',
		PIR_DM_OPZIONE_ISCRIZIONE,
		array( 'sanitize_callback' => 'esc_url_raw' )
	);
}
add_action( 'admin_init', 'pir_dm_registra_opzioni' );

function pir_dm_pagina_opzioni() {
	if ( isset( $_GET['pir_dm_pubblica'] ) && check_admin_referer( 'pir_dm_pubblica' ) ) {
		$pagine = get_posts( array( 'post_type' => 'page', 'post_status' => 'private', 'numberposts' => -1, 's' => '[dati_mercati' ) );
		foreach ( $pagine as $pagina ) {
			if ( false !== strpos( $pagina->post_content, '[dati_mercati' ) ) {
				wp_update_post( array( 'ID' => $pagina->ID, 'post_status' => 'publish' ) );
			}
		}
		echo '<div class="updated"><p>Pagine pubblicate: ora sono visibili a tutti.</p></div>';
	}
	if ( isset( $_GET['pir_dm_svuota'] ) && check_admin_referer( 'pir_dm_svuota' ) ) {
		global $wpdb;
		$wpdb->query( "DELETE FROM {$wpdb->options} WHERE option_name LIKE '_transient_pir_dm_%' OR option_name LIKE '_transient_timeout_pir_dm_%'" ); // phpcs:ignore
		echo '<div class="updated"><p>Cache svuotata: la pagina rilegge i file adesso.</p></div>';
	}
	$base = get_option( PIR_DM_OPZIONE, '' );
	?>
	<div class="wrap">
		<h1>Dati e mercati</h1>
		<form method="post" action="options.php">
			<?php settings_fields( 'pir_dm' ); ?>
			<table class="form-table">
				<tr>
					<th scope="row"><label for="pir_dm_url_base">Indirizzo dei file pubblicati</label></th>
					<td>
						<input type="url" id="pir_dm_url_base" name="<?php echo esc_attr( PIR_DM_OPZIONE ); ?>"
							value="<?php echo esc_attr( $base ); ?>" class="regular-text"
							placeholder="https://nome-utente.github.io/pesceinrete-dati-mercati/">
						<p class="description">
							L'indirizzo di GitHub Pages del repository. Con questo campo compilato i dati sul sito
							si aggiornano da soli; vuoto, il plugin usa la copia inclusa (ferma alla data del pacchetto).
							Da qui arrivano solo dati: le pagine e gli script restano quelli inclusi nel plugin.
						</p>
					</td>
				</tr>
				<tr>
					<th scope="row"><label for="pir_dm_url_iscrizione">Modulo di iscrizione al bollettino</label></th>
					<td>
						<input type="url" id="pir_dm_url_iscrizione" name="<?php echo esc_attr( PIR_DM_OPZIONE_ISCRIZIONE ); ?>"
							value="<?php echo esc_attr( get_option( PIR_DM_OPZIONE_ISCRIZIONE, '' ) ); ?>" class="regular-text"
							placeholder="https://… (indirizzo di invio del modulo Brevo, Mailchimp, MailerLite)">
						<p class="description">
							L'indirizzo a cui il servizio di newsletter riceve le iscrizioni (il campo "action" del suo modulo).
							Compilato, in pagina compare il riquadro "Ricevi il bollettino ogni giovedì" con l'indirizzo email.
						</p>
					</td>
				</tr>
			</table>
			<?php submit_button( 'Salva' ); ?>
		</form>
		<p>
			<a class="button" href="<?php echo esc_url( wp_nonce_url( admin_url( 'options-general.php?page=pir-dati-mercati&pir_dm_svuota=1' ), 'pir_dm_svuota' ) ); ?>">
				Svuota la cache (rilegge i file adesso)
			</a>
		</p>
		<h2>Pagine</h2>
		<p>Le pagine vengono create all'attivazione come <strong>private</strong>: le vedi solo tu, dentro il sito, con il tema vero.
			<a href="<?php echo esc_url( home_url( '/dati-mercati/' ) ); ?>">/dati-mercati/</a>
			e <a href="<?php echo esc_url( home_url( '/market-data/' ) ); ?>">/market-data/</a>, con una pagina figlia per specie.</p>
		<p>
			<a class="button button-primary" href="<?php echo esc_url( wp_nonce_url( admin_url( 'options-general.php?page=pir-dati-mercati&pir_dm_pubblica=1' ), 'pir_dm_pubblica' ) ); ?>">
				Pubblica le pagine (rendile visibili a tutti)
			</a>
		</p>
		<p>Se le cancelli, disattiva e riattiva il plugin per ricrearle.</p>
	</div>
	<?php
}
