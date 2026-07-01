# Node Store Frontend

A React-based storefront for discovering and searching computational nodes with faceted search capabilities.

## Features

- **Faceted Search**: Filter nodes by type, author, input/output datatypes
- **Semantic Search**: AI-powered search across node metadata
- **Keyword Search**: Traditional text-based search
- **Node Discovery**: Browse and explore available nodes
- **Responsive Design**: Works on desktop, tablet, and mobile devices using React Bootstrap

## Project Structure

```
src/
├── components/
│   ├── FacetedSearch.tsx      # Faceted search filter component
│   └── NodeCard.tsx            # Individual node card display
├── services/
│   └── api.ts                  # API integration with backend
├── types/
│   └── index.ts                # TypeScript type definitions
├── App.tsx                      # Main application component
├── App.css                      # Application styles
├── main.tsx                     # React entry point
└── index.css                    # Global styles
```

## Installation

1. Install dependencies:

```bash
npm install
```

2. Configure the API endpoint in `vite.config.ts` if needed (defaults to `http://localhost:8000/api`)

## Development

Start the development server:

```bash
npm run dev
```

The application will be available at `http://localhost:5173` and will proxy API requests to `http://localhost:8000/api`.

## Building

Build for production:

```bash
npm run build
```

Build output will be in the `dist/` directory.

## API Integration

The frontend connects to the Node Store backend API at `/api/v1`:

- `GET /api/v1/nodes` - List all nodes
- `GET /api/v1/nodes/{node_hash}` - Get node details
- `POST /api/v1/search` - Hybrid search (semantic + keyword); automatically falls back to keyword-only when AI/embeddings are unavailable. Set `semantic: false` in the body to force keyword-only.

## Technologies

- **React 18**: UI framework
- **TypeScript**: Type-safe development
- **React Bootstrap**: UI component library
- **Vite**: Build tool and dev server
- **Axios**: HTTP client for API communication
- **Lucide React**: Icon library

## Type Definitions

Key types from `src/types/index.ts`:

- `NodeMetadata`: Complete node information
- `NodeType`: Enum of node types (function, workflow, etc.)
- `FacetFilters`: Faceted search filter specifications
- `ScoredSearchResponse`: Search results with relevance scores

## Features in Detail

### Faceted Search

Filter results by:

- Node Type (function, workflow, etc.)
- Author
- Input Data Types
- Output Data Types

### Search Modes

- **Semantic Search**: Uses embeddings for intelligent search based on descriptions
- **Keyword Search**: Traditional text matching across node metadata

### Node Cards

Display node information including:

- Node type and import path
- Description and AI-generated summary
- Input/output count
- Dependencies
- Creator information and creation date

## Styling

The application uses Bootstrap 5 for responsive styling with custom CSS in `src/App.css` and `src/index.css`.

Custom styles include:

- Hover effects on node cards
- Sticky filter sidebar
- Responsive layout adjustments
- Dark navbar with brand styling
