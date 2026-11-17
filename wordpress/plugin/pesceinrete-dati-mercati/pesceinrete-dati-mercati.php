<?php
/**
 * Plugin Name: Pesceinrete — Dati e mercati
 * Description: Sezione di dati di mercato ittici: prezzi settimanali, posizione stagionale, importazioni italiane. Crea da sola le pagine e legge i dati dal repository.
 * Version: 1.0.0
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

define( 'PIR_DM_VERSIONE', '1.0.0' );
define( 'PIR_DM_CARTELLA', plugin_dir_path( __FILE__ ) . 'assets/' );
define( 'PIR_DM_INDIRIZZO', plugin_dir_url( __FILE__ ) . 'assets/' );
define( 'PIR_DM_OPZIONE', 'pir_dm_url_base' );
define( 'PIR_DM_OPZIONE_ISCRIZIONE', 'pir_dm_url_iscrizione' );

const PIR_DM_SPECIE = array(
	'salmone'     => array( 'Salmone', 'Salmon' ),
	'orata'       => array( 'Orata', 'Sea bream' ),
	'spigola'     => array( 'Spigola', 'Sea bass' ),
	'polpo'       => array( 'Polpo', 'Octopus' ),
	'gambero'     => array( 'Gambero', 'Shrimp' ),
	'merluzzo'    => array( 'Merluzzo', 'Cod' ),
	'tonno'       => array( 'Tonno', 'Tuna' ),
	'pesce_spada' => array( 'Pesce spada', 'Swordfish' ),
	'cozze'       => array( 'Cozze', 'Mussels' ),
	'vongole'     => array( 'Vongole', 'Clams' ),
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
	$html = preg_replace( '#<header class="pir-testata"[^>]*>.*?</header>#si', '', $html );
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
	return '<script>' . $avvio . '</script>' . $html;
}
add_shortcode( 'dati_mercati', 'pir_dm_shortcode' );

/* --------------------------------------------------------------------------
 * Pagine: create all'attivazione, una per specie, nelle due lingue
 * -------------------------------------------------------------------------- */

function pir_dm_crea_pagine() {
	foreach ( array( 'it' => 'dati-mercati', 'en' => 'market-data' ) as $lingua => $slug ) {
		$titolo = ( 'en' === $lingua ) ? 'Market data' : 'Dati e mercati';
		$padre  = pir_dm_assicura_pagina( $slug, $titolo, '[dati_mercati lingua="' . $lingua . '"]', 0 );
		foreach ( PIR_DM_SPECIE as $id => $nomi ) {
			$nome = ( 'en' === $lingua ) ? $nomi[1] : $nomi[0];
			pir_dm_assicura_pagina(
				$id,
				$nome,
				'[dati_mercati prodotto="' . $id . '" lingua="' . $lingua . '"]',
				$padre
			);
		}
	}
	flush_rewrite_rules();
}
register_activation_hook( __FILE__, 'pir_dm_crea_pagine' );

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

function pir_dm_e_pagina_sezione() {
	$post = get_queried_object();
	if ( ! $post || ! isset( $post->post_name ) ) {
		return false;
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
	$slug = get_post_field( 'post_name', get_queried_object_id() );
	foreach ( $dati['prodotti'] as $voce ) {
		if ( $voce['id'] === $slug ) {
			return $voce;
		}
	}
	return $dati['prodotti'][0];
}

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
	printf( '<link rel="alternate" hreflang="it" href="%s">' . "\n", esc_url( home_url( '/dati-mercati/' . $figlia ) ) );
	printf( '<link rel="alternate" hreflang="en" href="%s">' . "\n", esc_url( home_url( '/market-data/' . $figlia ) ) );
	printf( '<link rel="alternate" hreflang="x-default" href="%s">' . "\n", esc_url( home_url( '/dati-mercati/' . $figlia ) ) );
}
add_action( 'wp_head', 'pir_dm_testa', 1 );

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
