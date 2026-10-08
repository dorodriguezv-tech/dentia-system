from app.voice import nlu_fast


def test_strip_wake_word_removes_the_leading_dentia() -> None:
    assert nlu_fast.strip_wake_word("Dentia, abre la agenda") == "abre la agenda"


def test_strip_wake_word_is_accent_and_case_insensitive() -> None:
    assert nlu_fast.strip_wake_word("DENTÍA abre la agenda") == "abre la agenda"
    assert nlu_fast.strip_wake_word("dentia, abre la agenda") == "abre la agenda"


def test_strip_wake_word_without_dentia_prefix_is_unchanged_content() -> None:
    assert nlu_fast.strip_wake_word("abre la agenda") == "abre la agenda"


def test_match_returns_none_for_empty_or_wake_word_only() -> None:
    assert nlu_fast.match("") is None
    assert nlu_fast.match("Dentia") is None
    assert nlu_fast.match("   ") is None


def test_match_help() -> None:
    assert nlu_fast.match("Dentia, ayuda").intent == "ayuda"
    assert nlu_fast.match("¿qué puedo decir?").intent == "ayuda"


def test_match_repeat() -> None:
    assert nlu_fast.match("Dentia, repite").intent == "repetir"
    assert nlu_fast.match("¿qué dijiste?").intent == "repetir"


def test_match_silence() -> None:
    assert nlu_fast.match("Dentia, silencio").intent == "silencio"
    assert nlu_fast.match("cállate").intent == "silencio"


def test_match_leer_alertas() -> None:
    assert nlu_fast.match("Dentia, ¿tiene alergias?").intent == "leer_alertas"
    assert nlu_fast.match("dime las alertas").intent == "leer_alertas"
    assert nlu_fast.match("¿qué alertas tiene?").intent == "leer_alertas"


def test_match_citas_hoy() -> None:
    assert nlu_fast.match("Dentia, ¿qué citas tengo hoy?").intent == "citas_hoy"
    assert nlu_fast.match("¿quién sigue?").intent == "citas_hoy"


def test_match_abrir_expediente_with_full_phrase() -> None:
    result = nlu_fast.match("Dentia, abre el expediente de Juan Pérez")
    assert result.intent == "abrir_expediente"
    assert result.slots["query"] == "juan perez"


def test_match_abrir_expediente_with_busca() -> None:
    result = nlu_fast.match("Dentia, busca a María López")
    assert result.intent == "abrir_expediente"
    assert result.slots["query"] == "maria lopez"


def test_match_ir_a_with_verb() -> None:
    result = nlu_fast.match("Dentia, ve a la agenda")
    assert result.intent == "ir_a"
    assert result.slots["destino"] == "agenda"


def test_match_ir_a_single_word() -> None:
    result = nlu_fast.match("Dentia, odontograma")
    assert result.intent == "ir_a"
    assert result.slots["destino"] == "odontograma"


def test_match_unrecognized_phrase_returns_none() -> None:
    assert nlu_fast.match("Dentia, cuéntame un chiste") is None


def test_match_iniciar_consulta() -> None:
    assert nlu_fast.match("Dentia, inicia la consulta").intent == "iniciar_consulta"
    assert nlu_fast.match("empieza la atención").intent == "iniciar_consulta"


def test_match_deshacer() -> None:
    assert nlu_fast.match("Dentia, deshaz").intent == "deshacer"
    assert nlu_fast.match("quita lo ultimo").intent == "deshacer"


def test_match_hallazgo_with_article_and_surface() -> None:
    result = nlu_fast.match("Dentia, la 18 caries oclusal")
    assert result.intent == "hallazgo"
    assert result.slots == {"tooth_fdi": "18", "finding_code": "caries", "surfaces": "O"}


def test_match_hallazgo_with_multiple_surfaces() -> None:
    result = nlu_fast.match("la 18 tiene caries oclusal y distal")
    assert result.intent == "hallazgo"
    assert result.slots["surfaces"] == "O,D"


def test_match_hallazgo_without_surface() -> None:
    result = nlu_fast.match("la 28 ausente")
    assert result.intent == "hallazgo"
    assert result.slots == {"tooth_fdi": "28", "finding_code": "ausente", "surfaces": ""}


def test_match_hallazgo_with_pieza_trigger_word() -> None:
    result = nlu_fast.match("pieza 36 endodoncia")
    assert result.intent == "hallazgo"
    assert result.slots["tooth_fdi"] == "36"
    assert result.slots["finding_code"] == "endodoncia"


def test_match_hallazgo_requires_a_tooth_mention_with_trigger_word() -> None:
    # Limitacion conocida de esta etapa (ver docs/PENDIENTES_CLINICOS.md):
    # dental_parser.extract_tooth_mentions exige un articulo/disparador antes
    # del numero ("la 18", "pieza 18") -- un numero suelto como "dieciocho
    # ausente" no se reconoce todavia por la ruta rapida.
    assert nlu_fast.match("dieciocho ausente") is None


def test_match_hallazgo_without_a_finding_keyword_is_not_recognized() -> None:
    assert nlu_fast.match("revisa la 18") is None


def test_match_confirmation_recognizes_confirm_and_cancel_phrases() -> None:
    assert nlu_fast.match_confirmation("sí") == "confirm"
    assert nlu_fast.match_confirmation("correcto") == "confirm"
    assert nlu_fast.match_confirmation("ok") == "confirm"
    assert nlu_fast.match_confirmation("no") == "cancel"
    assert nlu_fast.match_confirmation("cancela") == "cancel"
    assert nlu_fast.match_confirmation("espera") == "cancel"


def test_match_confirmation_ignores_unrelated_speech() -> None:
    # Importante: no por palabra suelta dentro de una frase larga (ver
    # docstring de match_confirmation) -- si no, cualquier "no" dicho de paso
    # cancelaria una captura en curso.
    assert nlu_fast.match_confirmation("no sé doctor, pregúntele a él") is None
    assert nlu_fast.match_confirmation("hola buenas tardes") is None


def test_match_agendar_cita_with_date_time_and_provider() -> None:
    result = nlu_fast.match(
        "Dentia, agenda a Maria Lopez el jueves a las 11 con la doctora Ruiz, limpieza"
    )
    assert result.intent == "agendar_cita"
    assert result.slots["patient_query"] == "maria lopez"
    assert result.slots["date_text"] == "jueves"
    assert result.slots["time_text"] == "a las 11"
    assert result.slots["provider_query"] == "ruiz limpieza"


def test_match_agendar_cita_con_doctor_sin_articulo() -> None:
    result = nlu_fast.match("agenda a Juan Perez mañana a las 10 con doctor Gomez")
    assert result.intent == "agendar_cita"
    assert result.slots["date_text"] == "manana"
    assert result.slots["provider_query"] == "gomez"


def test_match_agendar_cita_hoy_sin_articulo_el() -> None:
    result = nlu_fast.match("agenda a Juan Perez hoy a las 10 con dra Ruiz")
    assert result.slots["date_text"] == "hoy"
    assert result.slots["provider_query"] == "ruiz"


def test_match_agendar_cita_without_a_patient_is_not_recognized() -> None:
    assert nlu_fast.match("agenda a") is None


def test_match_reprogramar_cita_with_date_and_time() -> None:
    result = nlu_fast.match("mueve la cita de Maria Lopez al viernes a las 10")
    assert result.intent == "reprogramar_cita"
    assert result.slots["patient_query"] == "maria lopez"
    assert result.slots["date_text"] == "viernes"
    assert result.slots["time_text"] == "a las 10"


def test_match_reprogramar_cita_without_a_new_time_keeps_it_empty() -> None:
    result = nlu_fast.match("reprograma la cita de Maria Lopez al viernes")
    assert result.intent == "reprogramar_cita"
    assert result.slots["time_text"] == ""


def test_match_confirmar_cita_by_patient_name() -> None:
    result = nlu_fast.match("confirma la cita de Maria Lopez")
    assert result.intent == "confirmar_cita"
    assert result.slots["patient_query"] == "maria lopez"
    assert result.slots["time_text"] == ""


def test_match_confirmar_cita_by_time() -> None:
    result = nlu_fast.match("confirma la cita de las 10")
    assert result.intent == "confirmar_cita"
    assert result.slots["patient_query"] == ""
    assert result.slots["time_text"] == "a las 10"


def test_match_registrar_llegada() -> None:
    result = nlu_fast.match("llegó Maria Lopez")
    assert result.intent == "registrar_llegada"
    assert result.slots["patient_query"] == "maria lopez"


def test_match_modo_dictado() -> None:
    assert nlu_fast.match("Dentia, dictado").intent == "modo_dictado"


def test_match_huecos_libres_with_provider_and_week() -> None:
    result = nlu_fast.match("Dentia, qué horarios libres tiene con la doctora Ruiz esta semana")
    assert result.intent == "huecos_libres"
    assert result.slots["provider_query"] == "ruiz"
    assert result.slots["date_text"] == "esta semana"


def test_match_huecos_libres_with_a_specific_day() -> None:
    result = nlu_fast.match("cuando hay espacio con el doctor Gomez mañana")
    assert result.intent == "huecos_libres"
    assert result.slots["provider_query"] == "gomez"
    assert result.slots["date_text"] == "manana"


def test_match_cancelar_cita_by_time_with_reason() -> None:
    result = nlu_fast.match("Dentia, cancela la cita de las 12, motivo: enfermedad")
    assert result.intent == "cancelar_cita"
    assert result.slots["time_text"] == "a las 12"
    assert result.slots["reason"] == "enfermedad"


def test_match_cancelar_cita_by_name_without_reason_leaves_it_empty() -> None:
    result = nlu_fast.match("cancela la cita de Maria Lopez")
    assert result.intent == "cancelar_cita"
    assert result.slots["patient_query"] == "maria lopez"
    assert result.slots["reason"] == ""


def test_match_no_show_prefix_phrasing() -> None:
    result = nlu_fast.match("no se presentó Maria Lopez")
    assert result.intent == "no_show"
    assert result.slots["patient_query"] == "maria lopez"


def test_match_no_show_suffix_phrasing() -> None:
    result = nlu_fast.match("Maria Lopez no llegó")
    assert result.intent == "no_show"
    assert result.slots["patient_query"] == "maria lopez"


def test_match_lista_espera_with_explicit_name() -> None:
    result = nlu_fast.match("agrega a Maria Lopez a la lista de espera")
    assert result.intent == "lista_espera"
    assert result.slots["patient_query"] == "maria lopez"


def test_match_lista_espera_pronoun_leaves_patient_query_empty() -> None:
    result = nlu_fast.match("agrégala a la lista de espera")
    assert result.intent == "lista_espera"
    assert result.slots["patient_query"] == ""


def test_match_alta_rapida_paciente_with_phone() -> None:
    result = nlu_fast.match("registra paciente nuevo Pedro Sanchez, telefono 555 123 4567")
    assert result.intent == "alta_rapida_paciente"
    assert result.slots["patient_name"] == "pedro sanchez"
    assert result.slots["phone"] == "5551234567"


def test_match_alta_rapida_paciente_without_phone() -> None:
    result = nlu_fast.match("nuevo paciente Pedro Sanchez")
    assert result.intent == "alta_rapida_paciente"
    assert result.slots["patient_name"] == "pedro sanchez"
    assert result.slots["phone"] == ""


def test_match_diagnostico_with_pon_un_diagnostico_de() -> None:
    result = nlu_fast.match(
        "Dentia, pon un diagnóstico de pulpitis reversible en la treinta y seis"
    )
    assert result.intent == "diagnostico"
    assert result.slots["text"] == "pulpitis reversible en la treinta y seis"
    assert result.slots["tooth_fdi"] == "36"


def test_match_diagnostico_with_colon_prefix_without_a_tooth() -> None:
    result = nlu_fast.match("diagnóstico: caries profunda")
    assert result.intent == "diagnostico"
    assert result.slots["text"] == "caries profunda"
    assert result.slots["tooth_fdi"] == ""


def test_match_procedimiento_planeado_does_not_collide_with_hallazgo() -> None:
    # "resina" es palabra clave de hallazgo (-> restauracion) -- debe ganar
    # procedimiento_planeado porque el verbo "planea" es mas especifico.
    result = nlu_fast.match("Dentia, planea una resina en la 36")
    assert result.intent == "procedimiento_planeado"
    assert result.slots["tooth_fdi"] == "36"
    assert "resina" in result.slots["full_text"]


def test_match_procedimiento_planeado_with_explicit_prefix() -> None:
    result = nlu_fast.match("procedimiento planeado limpieza")
    assert result.intent == "procedimiento_planeado"
    assert result.slots["full_text"] == "limpieza"
    assert result.slots["tooth_fdi"] == ""


def test_match_procedimiento_realizado_with_hice() -> None:
    result = nlu_fast.match("Dentia, hice una endodoncia en la 36")
    assert result.intent == "procedimiento_realizado"
    assert result.slots["tooth_fdi"] == "36"
    assert "endodoncia" in result.slots["full_text"]


def test_match_procedimiento_realizado_with_termine() -> None:
    result = nlu_fast.match("termine la limpieza")
    assert result.intent == "procedimiento_realizado"
    assert result.slots["full_text"] == "limpieza"
    assert nlu_fast.match("inicia el dictado").intent == "modo_dictado"


def test_is_dictation_end() -> None:
    assert nlu_fast.is_dictation_end("fin del dictado") is True
    assert nlu_fast.is_dictation_end("Termina el dictado") is True
    assert nlu_fast.is_dictation_end("ya terminé") is True
    assert nlu_fast.is_dictation_end("alérgica a la penicilina") is False
