# AAS Digital Nameplate Provider

This provider reads an Asset Administration Shell (AAS) JSON document with a `Nameplate` submodel and exposes selected values as Digital Product Memory product passport data.

The example AAS is stored in:

```text
data/example_digital_nameplate_aas.json
```

It follows the relevant structure of the IDTA Digital Nameplate submodel template:

- Submodel `Nameplate`
- semantic ID `https://admin-shell.io/zvei/nameplate/2/0/Nameplate`
- `URIOfTheProduct`
- `ManufacturerName`
- `ManufacturerProductDesignation`
- `ManufacturerProductType`
- `SerialNumber`
- `YearOfConstruction`
- `DateOfManufacture`
- `CountryOfOrigin`
- `Markings`

## Mapping to Digital Product Memory

| AAS Digital Nameplate element | Digital Product Memory field |
| --- | --- |
| `URIOfTheProduct` | `product_id` |
| `ManufacturerName` | `manufacturer` |
| `ManufacturerProductDesignation` | `model` |
| `ManufacturerProductType` | `product_type` inference and `specifications.manufacturer_product_type` |
| `SerialNumber` | `serial_number` |
| `DateOfManufacture` | `manufacturing_date` |
| `CountryOfOrigin` | `manufacturing_location` and `specifications.country_of_origin` |
| `Markings` | `certifications` and `compliance` |

## Endpoints

```text
GET  /health
GET  /.well-known/circthread-service
GET  /metadata
GET  /products
GET  /products/{product_id}
GET  /aas/{product_id}
POST /aas/ingest
```

`POST /aas/ingest` accepts another AAS JSON document and stores the parsed product in memory.

## Docker Compose Base URL

When this service runs in Docker Compose, register this URL in the Service Registry:

```text
http://aas-nameplate-provider:8023
```

When the provider runs locally on the host and the Registry runs in Docker, use:

```text
http://host.docker.internal:8023
```
