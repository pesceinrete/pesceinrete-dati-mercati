<?php
/**
 * Sezione "Dati e mercati" di Pesceinrete.
 *
 * Installazione:
 *   1. copiare questo file in wp-content/themes/<tema-figlio>/inc/
 *   2. aggiungere in functions.php del tema figlio:
 *        require_once get_stylesheet_directory() . '/inc/pesceinrete-dati-mercati.php';
 *   3. copiare la cartella consegna/dati-mercati/ del progetto in
 *        wp-content/themes/<tema-figlio>/dati-mercati/
 *      (contiene le due pagine HTML e la sottocartella data/ con prodotti/)
 *   4. creare la pagina "Dati e mercati" con indirizzo /dati-mercati/,
 *      modello a larghezza piena, e inserire lo shortcode [dati_mercati]
 *   5. consigliato: una pagina figlia per specie, /dati-mercati/orata/
 *      con [dati_mercati prodotto="orata"], e nel functions.php:
 *        add_filter( 'pir_dm_url_prodotto', fn() => home_url( '/dati-mercati/{id}/' ) );
 *
 * Non richiede plugin, non scrive nel database, non modifica il menu.
 *
 * @package Pesceinrete
 */

defined( 'ABSPATH' ) || exit;

const PIR_DM_CARTELLA = '/dati-mercati/';

/**
 * Percorso su disco della cartella della sezione.
 */
function pir_dm_percorso( $file = '' ) {
	return get_stylesheet_directory() . PIR_DM_CARTELLA . $file;
}

/**
 * Indirizzo pubblico della cartella della sezione.
 */
function pir_dm_indirizzo( $file = '' ) {
	return get_stylesheet_directory_uri() . PIR_DM_CARTELLA . $file;
}

/**
 * Versione basata sulla data del file dei dati.
 *
 * Serve a rinfrescare la cache del browser e dei plugin di cache ogni
 * volta che l'aggiornamento automatico pubblica dati nuovi, e solo allora.
 */
function pir_dm_versione() {
	$data = pir_dm_percorso( 'data/mercati.json' );
	return file_exists( $data ) ? (string) filemtime( $data ) : (string) time();
}

/**
 * Shortcode [dati_mercati].
 */
function pir_dm_shortcode( $attributi = array() ) {
	$attributi = shortcode_atts(
		array( 'prodotto' => 'salmone', 'lingua' => 'it' ),
		$attributi,
		'dati_mercati'
	);
	$lingua   = ( 'en' === $attributi['lingua'] ) ? 'en' : 'it';
	$suffisso = ( 'en' === $lingua ) ? '.en' : '';

	$pagina = pir_dm_percorso( 'dati-mercati' . $suffisso . '.html' );
	if ( ! file_exists( $pagina ) ) {
		return '<p>Sezione dati non disponibile. Contattare la redazione.</p>';
	}

	$html = file_get_contents( $pagina ); // phpcs:ignore WordPress.WP.AlternativeFunctions

	// Il tema fornisce testata, menu e piede: della pagina serve il corpo.
	// Lo stile della pagina sta nell'<head>: va conservato prima di tenere solo il <body>.
	$stile = '';
	if ( preg_match( '#<style\b[^>]*>.*?</style>#si', $html, $blocco ) ) {
		$stile = $blocco[0];
	}
	if ( preg_match( '#<body[^>]*>(.*)</body>#si', $html, $parti ) ) {
		$html = $stile . $parti[1];
	}
	// Testata e logo servono solo all'anteprima fuori dal sito.
	$html = preg_replace( '#<header class="pir-testata"[^>]*>.*?</header>#si', '', $html );
	$html = preg_replace( '#<a [^>]*data-solo-anteprima[^>]*>.*?</a>#si', '', $html );

	/**
	 * Indirizzo del file dei dati.
	 *
	 * Per impostazione predefinita è il file caricato nel tema. Con il
	 * filtro si può puntare a una fonte esterna, per esempio i file
	 * pubblicati dal repository, e non caricare più niente via FTP.
	 */
	$url_locale = pir_dm_indirizzo( 'data/mercati' . $suffisso . '.json' ) . '?v=' . pir_dm_versione();
	$url_dati   = apply_filters( 'pir_dm_url_dati', $url_locale );
	$remoto     = ( $url_dati !== $url_locale );

	// Blocco statico di sintesi: testo vero, indicizzabile e leggibile
	// anche senza JavaScript. Va inserito lato server, e deve venire dalla
	// stessa origine dei dati, altrimenti tabella e grafici divergono.
	$prodotto = sanitize_key( $attributi['prodotto'] ) . $suffisso;
	$sintesi  = pir_dm_sintesi( $prodotto, $remoto ? $url_dati : '' );
	if ( $sintesi ) {
		$html = str_replace(
			'<div id="pir-sintesi-statica"></div>',
			'<div id="pir-sintesi-statica">' . $sintesi . '</div>',
			$html
		);
	}
	$url_dati = esc_url( $url_dati );

	/**
	 * Una pagina per specie, consigliata: /dati-mercati/orata/ ecc. Con il
	 * filtro si indica lo schema degli indirizzi e il selettore in pagina
	 * diventa un elenco di collegamenti, uno per specie, invece di
	 * cambiare specie sul posto. Ogni specie ha così titolo, descrizione e
	 * testo statico propri, che è quello che i motori di ricerca indicizzano.
	 */
	$schema_prodotto = apply_filters( 'pir_dm_url_prodotto', '' );

	$avvio  = 'window.PESCEINRETE_URL_DATI=' . wp_json_encode( $url_dati ) . ';';
	$avvio .= 'window.PESCEINRETE_PRODOTTO=' . wp_json_encode( sanitize_key( $attributi['prodotto'] ) ) . ';';
	if ( $schema_prodotto ) {
		$avvio .= 'window.PESCEINRETE_URL_PRODOTTO=' . wp_json_encode( $schema_prodotto ) . ';';
	}
	return '<script>' . $avvio . '</script>' . $html;
}
add_shortcode( 'dati_mercati', 'pir_dm_shortcode' );

/**
 * Titolo e descrizione della pagina presi dai dati pubblicati.
 *
 * Così il titolo in pagina dei risultati di ricerca cambia con il
 * prodotto e resta coerente con quello che la pagina mostra davvero.
 * Se sul sito c'è un plugin SEO che imposta già questi valori, questa
 * parte si può togliere senza conseguenze.
 */
/**
 * Le due pagine WordPress hanno slug "dati-mercati" (italiano) e
 * "market-data" (inglese). Ognuna legge il JSON della propria lingua.
 */
function pir_dm_lingua_pagina() {
	if ( is_page( 'market-data' ) ) {
		return 'en';
	}
	$post = get_queried_object();
	if ( $post && ! empty( $post->post_parent ) && 'market-data' === get_post_field( 'post_name', $post->post_parent ) ) {
		return 'en';
	}
	return 'it';
}

/**
 * La specie di questa pagina: lo slug della pagina figlia (/dati-mercati/orata/)
 * oppure, sulla pagina principale, la prima del registro.
 */
function pir_dm_voce_pagina() {
	$dati = pir_dm_dati_pubblicati( pir_dm_lingua_pagina() );
	if ( ! $dati || empty( $dati['prodotti'] ) ) {
		return null;
	}
	$slug = get_post_field( 'post_name', get_queried_object_id() );
	foreach ( $dati['prodotti'] as $voce ) {
		if ( $voce['id'] === $slug ) {
			return $voce;
		}
	}
	return $dati['prodotti'][0];
}

function pir_dm_e_pagina_sezione() {
	if ( is_page( array( 'dati-mercati', 'market-data' ) ) ) {
		return true;
	}
	$post = get_queried_object();
	if ( ! $post || empty( $post->post_parent ) ) {
		return false;
	}
	$padre = get_post_field( 'post_name', $post->post_parent );
	return in_array( $padre, array( 'dati-mercati', 'market-data' ), true );
}

function pir_dm_titolo( $titolo ) {
	if ( ! pir_dm_e_pagina_sezione() ) {
		return $titolo;
	}
	$voce = pir_dm_voce_pagina();
	if ( $voce && ! empty( $voce['titolo_pagina'] ) ) {
		return $voce['titolo_pagina'] . ' — Pesceinrete';
	}
	return $titolo;
}
add_filter( 'pre_get_document_title', 'pir_dm_titolo' );

function pir_dm_descrizione() {
	if ( ! pir_dm_e_pagina_sezione() ) {
		return;
	}
	$voce = pir_dm_voce_pagina();
	if ( $voce && ! empty( $voce['descrizione_pagina'] ) ) {
		printf(
			'<meta name="description" content="%s">' . "\n",
			esc_attr( $voce['descrizione_pagina'] )
		);
	}
}
add_action( 'wp_head', 'pir_dm_descrizione', 1 );

/**
 * Blocco di sintesi: dalla stessa origine dei dati.
 *
 * Con origine remota viene scaricato e tenuto in cache per un'ora; se il
 * repository non risponde si usa la copia locale, così la pagina non
 * resta mai senza il blocco statico.
 */
function pir_dm_sintesi( $prodotto, $url_dati_remoto = '' ) {
	$locale = pir_dm_percorso( 'data/sintesi-' . $prodotto . '.html' );

	if ( $url_dati_remoto ) {
		$chiave  = 'pir_dm_sintesi_' . $prodotto;
		$in_cache = get_transient( $chiave );
		if ( false !== $in_cache ) {
			return $in_cache;
		}
		$url_sintesi = preg_replace( '#mercati(\.en)?\.json(\?.*)?$#', 'sintesi-' . $prodotto . '.html', $url_dati_remoto );
		$risposta    = wp_remote_get( $url_sintesi, array( 'timeout' => 6 ) );
		if ( ! is_wp_error( $risposta ) && 200 === wp_remote_retrieve_response_code( $risposta ) ) {
			$corpo = wp_remote_retrieve_body( $risposta );
			if ( $corpo ) {
				set_transient( $chiave, $corpo, HOUR_IN_SECONDS );
				return $corpo;
			}
		}
	}

	return file_exists( $locale ) ? file_get_contents( $locale ) : ''; // phpcs:ignore WordPress.WP.AlternativeFunctions
}

/**
 * Legge il file dei dati una sola volta per richiesta.
 */
function pir_dm_dati_pubblicati( $lingua = 'it' ) {
	static $cache = array();
	if ( isset( $cache[ $lingua ] ) ) {
		return $cache[ $lingua ];
	}
	$percorso         = pir_dm_percorso( 'data/mercati' . ( 'en' === $lingua ? '.en' : '' ) . '.json' );
	$cache[ $lingua ] = file_exists( $percorso )
		? json_decode( file_get_contents( $percorso ), true ) // phpcs:ignore WordPress.WP.AlternativeFunctions
		: false;
	return $cache[ $lingua ];
}

/**
 * Collegamento fra le due versioni linguistiche, per i motori di ricerca.
 */
function pir_dm_hreflang() {
	if ( ! is_page( array( 'dati-mercati', 'market-data' ) ) ) {
		return;
	}
	printf( '<link rel="alternate" hreflang="it" href="%s">' . "\n", esc_url( home_url( '/dati-mercati/' ) ) );
	printf( '<link rel="alternate" hreflang="en" href="%s">' . "\n", esc_url( home_url( '/market-data/' ) ) );
	printf( '<link rel="alternate" hreflang="x-default" href="%s">' . "\n", esc_url( home_url( '/dati-mercati/' ) ) );
}
add_action( 'wp_head', 'pir_dm_hreflang', 2 );

/**
 * Data di ultima modifica reale della pagina.
 *
 * Una pagina di dati aggiornata ogni settimana deve dichiarare la data
 * vera, altrimenti nei risultati di ricerca sembra ferma al giorno in cui
 * è stata creata.
 */
function pir_dm_data_modifica( $data, $formato, $post ) {
	if ( ! $post || ! in_array( $post->post_name, array( 'dati-mercati', 'market-data' ), true ) ) {
		return $data;
	}
	$file = pir_dm_percorso( 'data/mercati.json' );
	return file_exists( $file ) ? date_i18n( $formato, filemtime( $file ) ) : $data;
}
add_filter( 'get_the_modified_date', 'pir_dm_data_modifica', 10, 3 );
