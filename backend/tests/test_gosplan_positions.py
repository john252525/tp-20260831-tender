"""Тесты извлечения позиций из ответа ГосПлан API.

Фикстуры повторяют реальные структуры v2test.gosplan.info:
* notDrugPurchaseObjectsInfo.purchaseObject (list и dict)
* drugPurchaseObjectsInfo.drugPurchaseObjectInfo (dict)
* purchaseObjectsInfo.purchaseObject на верхнем уровне (EZT)
"""

from app.services.gosplan_positions import (
    extract_customer,
    extract_description,
    extract_documents,
    extract_positions,
    extract_purchase_data,
)


def _detail(notification: dict, docs_extra: dict | None = None) -> dict:
    source = {'notificationInfo': notification}
    if docs_extra:
        source.update(docs_extra)
    return {
        'purchase_number': '0000000000000000000',
        'max_price': 100000.0,
        'contract_guarantee_amount': 5000.0,
        'object_info': 'Предмет закупки',
        'docs': [{'doc_type': 'epNotificationEF2020', 'source': source}],
    }


def test_positions_from_not_drug_list():
    """Обычные товары: purchaseObject — список, количество в quantity.value."""
    notification = {
        'purchaseObjectsInfo': {
            'notDrugPurchaseObjectsInfo': {
                'purchaseObject': [
                    {
                        'KTRU': {
                            'code': '25.99.29.120-00000003',
                            'name': 'Лопата',
                            'characteristics': {
                                'characteristicsUsingTextForm': [
                                    {
                                        'name': 'Наличие черенка',
                                        'values': {'value': {'qualityDescription': 'нет'}},
                                    }
                                ]
                            },
                        },
                        'OKEI': {'code': '796', 'nationalCode': 'шт', 'name': 'Штука'},
                        'quantity': {'value': '60.00000000000'},
                        'price': 3500.00,
                        'sum': 210000.00,
                        'name': 'Лопата',
                    }
                ]
            }
        }
    }
    positions = extract_positions(_detail(notification))

    assert len(positions) == 1
    position = positions[0]
    assert position['position_number'] == 1
    assert position['name'] == 'Лопата'
    assert position['quantity'] == 60.0
    assert position['unit'] == 'шт'
    assert position['okpd2'] == '25.99.29.120'
    assert 'Наличие черенка: нет' in position['characteristics']


def test_positions_quantity_undefined_defaults_to_zero():
    """Количество может прийти как {"undefined": "true"}."""
    notification = {
        'purchaseObjectsInfo': {
            'notDrugPurchaseObjectsInfo': {
                'purchaseObject': {
                    'KTRU': {'code': '32.50.13.110-00005349', 'name': 'Катетер'},
                    'OKEI': {'nationalCode': 'шт'},
                    'quantity': {'undefined': 'true'},
                    'name': 'Катетер ангиографический',
                }
            }
        }
    }
    positions = extract_positions(_detail(notification))

    assert len(positions) == 1
    assert positions[0]['quantity'] == 0.0
    assert positions[0]['unit'] == 'шт'


def test_positions_from_drug_info():
    """Лекарства: drugPurchaseObjectInfo, количество в drugQuantity."""
    notification = {
        'purchaseObjectsInfo': {
            'drugPurchaseObjectsInfo': {
                'drugPurchaseObjectInfo': {
                    'name': 'СОФОСБУВИР, ТАБЛЕТКИ',
                    'pricePerUnit': '1375.00',
                    'positionPrice': '1540000.00',
                    'objectInfoUsingReferenceInfo': {
                        'drugsInfo': {
                            'drugInfo': {
                                'OKPD2': {'OKPDCode': '21.20.10.194'},
                                'KTRU': {'code': '21.20.10.194-00031'},
                                'MNNInfo': {'MNNName': 'СОФОСБУВИР'},
                                'medicamentalFormInfo': {
                                    'medicamentalFormName': 'ТАБЛЕТКИ, ПОКРЫТЫЕ ОБОЛОЧКОЙ'
                                },
                                'dosageInfo': {'dosageGRLSValue': '400 мг'},
                                'manualUserOKEI': {'code': '796', 'name': 'шт'},
                                'drugQuantity': '1120',
                            }
                        }
                    },
                }
            }
        }
    }
    positions = extract_positions(_detail(notification))

    assert len(positions) == 1
    position = positions[0]
    assert position['quantity'] == 1120.0
    assert position['unit'] == 'шт'
    assert position['okpd2'] == '21.20.10.194'
    assert 'СОФОСБУВИР' in position['characteristics']
    assert 'ТАБЛЕТКИ, ПОКРЫТЫЕ ОБОЛОЧКОЙ' in position['characteristics']
    assert '400 мг' in position['characteristics']


def test_positions_from_top_level_purchase_object():
    """Малые закупки (EZT): purchaseObject на верхнем уровне."""
    notification = {
        'purchaseObjectsInfo': {
            'purchaseObject': {
                'KTRU': {'code': '02.20.14.130-00000001', 'name': 'Дрова'},
                'OKEI': {'nationalCode': 'куб.м', 'name': 'Кубический метр'},
                'quantity': {'value': '370.00000000000'},
                'price': 3500.00,
                'sum': 1295000.00,
            },
            'totalSum': 1295000.00,
            'type': 'PRODUCT',
        }
    }
    positions = extract_positions(_detail(notification))

    assert len(positions) == 1
    assert positions[0]['name'] == 'Дрова'
    assert positions[0]['quantity'] == 370.0
    assert positions[0]['unit'] == 'куб.м'
    assert positions[0]['okpd2'] == '02.20.14.130'


def test_documents_from_attachments_info():
    """Документы берутся из attachmentsInfo.attachmentInfo, а не из docs[].url."""
    detail = _detail(
        {'purchaseObjectsInfo': {}},
        docs_extra={
            'attachmentsInfo': {
                'attachmentInfo': [
                    {
                        'fileName': 'Описание объекта закупки.xlsx',
                        'fileSize': '17644',
                        'url': 'https://zakupki.gov.ru/44fz/filestore/public/1.0/download/priz/file.html?uid=ABC',
                    },
                    {'fileName': 'без-url.docx'},
                ]
            }
        },
    )
    documents = extract_documents(detail)

    assert len(documents) == 1
    assert documents[0]['filename'] == 'Описание объекта закупки.xlsx'
    assert documents[0]['file_size'] == 17644.0


def test_customer_and_description():
    detail = _detail(
        {
            'purchaseObjectsInfo': {},
            'customerRequirementsInfo': {
                'customerRequirementInfo': {
                    'customer': {
                        'fullName': 'ГОСУДАРСТВЕННОЕ ПРЕДПРИЯТИЕ "НОФ"',
                        'INN': '5260136299',
                        'KPP': '526001001',
                    }
                }
            },
        },
        docs_extra={'commonInfo': {'purchaseObjectInfo': 'Поставка медизделий'}},
    )
    customer = extract_customer(detail)
    assert customer['name'] == 'ГОСУДАРСТВЕННОЕ ПРЕДПРИЯТИЕ "НОФ"'
    assert customer['inn'] == '5260136299'
    assert extract_description(detail) == 'Поставка медизделий'


def test_extract_purchase_data_smoke():
    detail = _detail({'purchaseObjectsInfo': {}})
    data = extract_purchase_data(detail)

    assert set(data.keys()) == {'positions', 'requirements', 'documents', 'customer', 'description'}
    assert data['positions'] == []
    assert data['requirements']['security_bid'] == 5000.0

def test_duplicate_positions_are_merged_and_renumbered():
    """Дубли одной позиции (по заказчикам) объединяются, нумерация сквозная."""
    notification = {
        'purchaseObjectsInfo': {
            'notDrugPurchaseObjectsInfo': {
                'purchaseObject': [
                    {
                        'KTRU': {'code': '32.50.13.110-00005349', 'name': 'Катетер'},
                        'OKEI': {'nationalCode': 'шт'},
                        'quantity': {'value': '5'},
                        'name': 'Катетер ангиографический',
                    },
                    {
                        'KTRU': {'code': '32.50.13.110-00005349', 'name': 'Катетер'},
                        'OKEI': {'nationalCode': 'шт'},
                        'quantity': {'value': '7'},
                        'name': 'Катетер ангиографический',
                    },
                    {
                        'KTRU': {'code': '32.50.13.190-00007203', 'name': 'Интродьюсер'},
                        'OKEI': {'nationalCode': 'шт'},
                        'quantity': {'undefined': 'true'},
                        'name': 'Интродьюсер',
                    },
                ]
            }
        }
    }
    positions = extract_positions(_detail(notification))

    assert [p['position_number'] for p in positions] == [1, 2]
    assert positions[0]['quantity'] == 12.0
    assert positions[1]['name'] == 'Интродьюсер'

def test_positions_from_top_level_drug_objects_info():
    """Блок drugPurchaseObjectsInfo может лежать прямо в notificationInfo."""
    notification = {
        'customerRequirementsInfo': {},
        'drugPurchaseObjectsInfo': {
            'drugPurchaseObjectInfo': {
                'name': 'ЛЕВОКАРНИТИН',
                'pricePerUnit': '18.34',
                'positionPrice': '183400.00',
                'objectInfoUsingReferenceInfo': {
                    'drugsInfo': {
                        'drugInfo': {
                            'OKPD2': {'OKPDCode': '21.20.10.194'},
                            'KTRU': {'code': '21.20.10.194-00031'},
                            'MNNInfo': {'MNNName': 'ЛЕВОКАРНИТИН'},
                            'manualUserOKEI': {'code': '796', 'name': 'шт'},
                            'drugQuantity': '10000',
                        }
                    }
                },
            },
            'total': '183400.00',
        },
    }
    positions = extract_positions(_detail(notification))

    assert len(positions) == 1
    assert positions[0]['name'] == 'ЛЕВОКАРНИТИН'
    assert positions[0]['quantity'] == 10000.0

def test_drug_interchange_info_is_parsed():
    """Взаимозаменяемые лекарства: данные лежат в drugInterchangeInfo, а не drugInfo."""
    notification = {
        'purchaseObjectsInfo': {
            'drugPurchaseObjectsInfo': {
                'drugPurchaseObjectInfo': [
                    {
                        'name': 'АТРОПИН',
                        'positionPrice': '6573.00',
                        'pricePerUnit': '9.39',
                        'drugQuantityCustomersInfo': {
                            'drugQuantityCustomerInfo': {'quantity': '700'},
                            'total': '700',
                        },
                        'objectInfoUsingReferenceInfo': {
                            'drugsInfo': {
                                'drugInterchangeInfo': {
                                    'drugInterchangeReferenceInfo': {
                                        'isInterchange': 'true',
                                        'drugInfo': [
                                            {
                                                'drugInfoUsingReferenceInfo': {
                                                    'MNNInfo': {'MNNName': 'АТРОПИН'},
                                                    'OKPD2': {'OKPDCode': '21.20.10.113'},
                                                    'KTRU': {'code': '21.20.10.113-00009'},
                                                    'medicamentalFormInfo': {
                                                        'medicamentalFormName': 'РАСТВОР ДЛЯ ИНЪЕКЦИЙ'
                                                    },
                                                    'dosageInfo': {'dosageGRLSValue': '0.5 мг/мл'},
                                                    'manualUserOKEI': {'code': '111', 'name': 'см[3*];^мл'},
                                                },
                                                'drugQuantity': '1400',
                                            }
                                        ],
                                    }
                                }
                            }
                        },
                    }
                ]
            }
        }
    }
    positions = extract_positions(_detail(notification))

    assert len(positions) == 1
    position = positions[0]
    assert position['name'] == 'АТРОПИН'
    assert position['okpd2'] == '21.20.10.113'
    # total по заказчикам (700), а не вариант дозировки 1400 из drugInterchangeInfo
    assert position['quantity'] == 700.0
    assert position['unit'] == 'см[3*];^мл'


def test_drug_quantity_falls_back_to_customers_total():
    """Если drugQuantity отсутствует — берём total по заказчикам."""
    notification = {
        'purchaseObjectsInfo': {
            'drugPurchaseObjectsInfo': {
                'drugPurchaseObjectInfo': {
                    'name': 'ФЛУКОНАЗОЛ',
                    'positionPrice': '6375.60',
                    'drugQuantityCustomersInfo': {
                        'drugQuantityCustomerInfo': {'quantity': '425'},
                        'total': '425.00000000000',
                    },
                    'objectInfoUsingReferenceInfo': {
                        'drugsInfo': {
                            'drugInfo': {
                                'MNNInfo': {'MNNName': 'ФЛУКОНАЗОЛ'},
                                'manualUserOKEI': {'code': '796', 'name': 'шт'},
                            }
                        }
                    },
                }
            }
        }
    }
    positions = extract_positions(_detail(notification))

    assert positions[0]['quantity'] == 425.0


def test_quantity_fallback_from_sum_over_price():
    """При quantity=undefined количество оценивается как sum / price."""
    notification = {
        'purchaseObjectsInfo': {
            'notDrugPurchaseObjectsInfo': {
                'purchaseObject': {
                    'KTRU': {'code': '32.50.13.139-00003044', 'name': 'Степлер'},
                    'OKEI': {'nationalCode': 'шт'},
                    'quantity': {'undefined': 'true'},
                    'price': 6400.00,
                    'sum': 12800.00,
                    'name': 'Степлер циркулярный',
                }
            }
        }
    }
    positions = extract_positions(_detail(notification))

    assert positions[0]['quantity'] == 2.0

def test_drug_interchange_manual_info_is_parsed():
    """Ручная взаимозаменяемость: drugInterchangeManualInfo."""
    notification = {
        'purchaseObjectsInfo': {
            'drugPurchaseObjectsInfo': {
                'drugPurchaseObjectInfo': {
                    'name': 'Микофеноловая кислота',
                    'positionPrice': '45120.00',
                    'drugQuantityCustomersInfo': {'total': '240'},
                    'objectInfoUsingReferenceInfo': {
                        'drugsInfo': {
                            'drugInterchangeInfo': {
                                'drugInterchangeManualInfo': {
                                    'isInterchange': 'true',
                                    'drugInfo': [
                                        {
                                            'drugInfoUsingReferenceInfo': {
                                                'MNNInfo': {'MNNName': 'МИКОФЕНОЛОВАЯ КИСЛОТА'},
                                                'OKPD2': {'OKPDCode': '21.20.10.214'},
                                                'KTRU': {'code': '21.20.10.214-00021'},
                                                'medicamentalFormInfo': {
                                                    'medicamentalFormName': 'ТАБЛЕТКИ'
                                                },
                                                'dosageInfo': {'dosageGRLSValue': '500 мг'},
                                                'manualUserOKEI': {'code': '796', 'name': 'шт'},
                                            },
                                            'drugQuantity': '240',
                                        }
                                    ],
                                }
                            }
                        }
                    },
                }
            }
        }
    }
    positions = extract_positions(_detail(notification))

    assert len(positions) == 1
    assert positions[0]['okpd2'] == '21.20.10.214'
    assert positions[0]['quantity'] == 240.0
    assert 'ТАБЛЕТКИ' in positions[0]['characteristics']
