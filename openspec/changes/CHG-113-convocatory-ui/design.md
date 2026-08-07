# Design: CHG-113 - Interfaz HTML para Gestión de Convocatorias

## Technical Approach

Use Django Template Views with HTMX for dynamic interactions. Reuse existing services from CHG-201.

## URLs

| URL | View | Description |
|-----|------|-------------|
| `/convocatorias/` | ConvocatoryListView | List all |
| `/convocatorias/crear/` | ConvocatoryCreateView | Create new |
| `/convocatorias/<id>/` | ConvocatoryDetailView | Detail |
| `/convocatorias/<id>/editar/` | ConvocatoryUpdateView | Edit |
| `/convocatorias/<id>/transicionar/` | ConvocatoryTransitionView | State change |

## Views

- ConvocatoryListView - List with filters
- ConvocatoryCreateView - Create form
- ConvocatoryUpdateView - Edit form (only draft)
- ConvocatoryDetailView - Full detail + state history
- ConvocatoryTransitionView - POST to change state

## Templates

- `convocatories/index.html` - List
- `convocatories/detail.html` - Detail
- `convocatories/form.html` - Create/Edit
- `convocatories/transitions.html` - State buttons

## Permissions

- IsAdminOrCoordinator - for create/edit
- IsAdminRole - for close transition
