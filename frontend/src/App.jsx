import React, { useState, useEffect, useRef, useCallback } from 'react';
import {
    Search, ArrowLeft, Server, FileText,
    ChevronDown, AlertTriangle, Layers, Cpu, Package, Leaf,
    ShieldCheck, Trash2, DollarSign, Wrench,
    Database, Zap, Info, RefreshCw, User, Calendar, Plus, Wand2,
    ListChecks, CheckSquare, Square, Waypoints, QrCode, X, Camera,
    Wifi, Radio, LayoutGrid
} from 'lucide-react';
import { BrowserQRCodeReader } from '@zxing/browser';
import * as api from './api';
import circthreadLogo from './static/circthread_logo.png';

/* ─── Category icon mapping ────────────────────────────────────────────────── */

const CATEGORY_ICONS = {
    identification: FileText,
    technical: Cpu,
    components: Package,
    materials: Layers,
    sustainability: Leaf,
    safety: AlertTriangle,
    compliance: ShieldCheck,
    end_of_life: Trash2,
    economic: DollarSign,
    maintenance: Wrench,
    metadata: Database,
};

const CATEGORY_DISPLAY = {
    identification: 'Product Identification',
    technical: 'Technical Specifications',
    components: 'Product Components',
    materials: 'Material Composition',
    sustainability: 'Sustainability Metrics',
    safety: 'Safety Information',
    compliance: 'Regulatory Compliance',
    end_of_life: 'End of Life',
    economic: 'Economic Data',
    maintenance: 'Maintenance & Repair',
    metadata: 'Data Metadata',
};

const PRODUCT_TYPE_LABELS = {
    washing_machine: 'Washing Machine',
    dishwasher: 'Dishwasher',
    boiler: 'Boiler',
    solar_panel: 'Solar Panel',
    lithium_battery: 'Lithium Battery',
};

const SKOS_MATCH_DESCRIPTIONS = {
    'skos:exactMatch': {
        label: 'Exact match',
        description: 'The two concepts can be used interchangeably for this mapping context.',
    },
    'skos:closeMatch': {
        label: 'Close match',
        description: 'The concepts are sufficiently similar for many uses, but not fully identical.',
    },
    'skos:narrowMatch': {
        label: 'Narrower match',
        description: 'The target concept is more specific than the Digital Product Memory source concept.',
    },
    'skos:broadMatch': {
        label: 'Broader match',
        description: 'The target concept is more general than the Digital Product Memory source concept.',
    },
    'skos:relatedMatch': {
        label: 'Related match',
        description: 'The concepts are associated, but the relation is not hierarchical or equivalent.',
    },
};

/* ─── Helpers ──────────────────────────────────────────────────────────────── */

function formatValue(value) {
    if (value === null || value === undefined) return '—';
    if (typeof value === 'boolean') return value ? 'Yes' : 'No';
    if (typeof value === 'number') return value.toLocaleString();
    if (typeof value === 'string') return value;
    if (Array.isArray(value)) {
        if (value.length === 0) return '—';
        if (typeof value[0] === 'string') return value.join(', ');
        return JSON.stringify(value, null, 2);
    }
    if (typeof value === 'object') return JSON.stringify(value, null, 2);
    return String(value);
}

function isComplexValue(value) {
    return (Array.isArray(value) && value.length > 0 && typeof value[0] === 'object')
        || (typeof value === 'object' && value !== null && !Array.isArray(value));
}

function priorityClass(p) {
    if (p >= 0.8) return 'high';
    if (p >= 0.5) return 'medium';
    return 'low';
}

function prettifyKey(key) {
    return key
        .replace(/_/g, ' ')
        .replace(/\b\w/g, c => c.toUpperCase());
}

function getSkosMatchInfo(predicateId) {
    return SKOS_MATCH_DESCRIPTIONS[predicateId] || {
        label: predicateId || 'Mapping predicate',
        description: 'SSSOM mapping predicate for the relationship between source and target term.',
    };
}

function renderBadge(label, tone = 'neutral') {
    return <span className={`data-badge ${tone}`}>{label}</span>;
}

function contextLabel(value, fallback) {
    return value || fallback;
}

function recommendationModeLabel(mode) {
    const labels = {
        role_event: 'Role + event',
        role: 'Role only',
        event: 'Event only',
        generic: 'Generic fields',
        role_fallback: 'Role (fallback)',
        basic_fallback: 'Basic fields',
        dynamic: 'Dynamic template',
    };
    return labels[mode] || 'Recommendation';
}

function renderMaterialList(items) {
    return (
        <div className="material-list">
            {items.map((item, index) => {
                const percentage = Number(item.percentage || 0);
                return (
                    <div key={`${item.material}-${index}`} className="material-item">
                        <div className="material-main">
                            <div className="material-name">{item.material || `Material ${index + 1}`}</div>
                            <div className="material-badges">
                                {renderBadge(item.recyclable ? 'Recyclable' : 'Not recyclable', item.recyclable ? 'green' : 'neutral')}
                                {item.hazardous && renderBadge('Hazardous', 'red')}
                            </div>
                        </div>
                        <div className="material-meter" aria-label={`${percentage}%`}>
                            <span style={{ width: `${Math.min(Math.max(percentage, 0), 100)}%` }} />
                        </div>
                        <div className="material-percent">{percentage}%</div>
                    </div>
                );
            })}
        </div>
    );
}

function renderComponentList(items) {
    return (
        <div className="object-list">
            {items.map((item, index) => (
                <div key={`${item.name}-${index}`} className="object-item">
                    <div className="object-title-row">
                        <div>
                            <div className="object-title">{item.name || `Component ${index + 1}`}</div>
                            {item.part_number && <div className="object-subtitle">{item.part_number}</div>}
                        </div>
                        <div className="object-badges">
                            {renderBadge(item.replaceable ? 'Replaceable' : 'Fixed', item.replaceable ? 'green' : 'neutral')}
                            {item.expected_lifetime_years && renderBadge(`${item.expected_lifetime_years} years`, 'blue')}
                        </div>
                    </div>
                    {Array.isArray(item.materials) && item.materials.length > 0 && (
                        <div className="nested-materials">
                            {renderMaterialList(item.materials)}
                        </div>
                    )}
                </div>
            ))}
        </div>
    );
}

function renderHazardList(items) {
    return (
        <div className="object-list">
            {items.map((item, index) => (
                <div key={`${item.name}-${index}`} className="object-item hazard">
                    <div className="object-title-row">
                        <div>
                            <div className="object-title">{item.name || `Substance ${index + 1}`}</div>
                            {item.cas_number && <div className="object-subtitle">CAS {item.cas_number}</div>}
                        </div>
                        <div className="object-badges">
                            {item.regulation && renderBadge(item.regulation, 'red')}
                            {item.concentration_pct !== null && item.concentration_pct !== undefined && renderBadge(`${item.concentration_pct}%`, 'neutral')}
                        </div>
                    </div>
                    {item.safety_instructions && (
                        <div className="object-note">{item.safety_instructions}</div>
                    )}
                </div>
            ))}
        </div>
    );
}

function renderScheduleList(items) {
    return (
        <div className="timeline-list">
            {items.map((item, index) => (
                <div key={`${item.task}-${index}`} className="timeline-item">
                    <div className="timeline-marker">{item.interval_months ? `${item.interval_months}m` : index + 1}</div>
                    <div className="timeline-content">{item.task || formatValue(item)}</div>
                </div>
            ))}
        </div>
    );
}

function renderObjectGrid(value) {
    return (
        <div className="object-grid">
            {Object.entries(value).map(([key, val]) => (
                <div key={key} className="object-grid-row">
                    <span>{prettifyKey(key)}</span>
                    <strong>{formatValue(val)}</strong>
                </div>
            ))}
        </div>
    );
}

function renderGenericObjectList(items) {
    return (
        <div className="object-list">
            {items.map((item, index) => (
                <div key={index} className="object-item">
                    {renderObjectGrid(item)}
                </div>
            ))}
        </div>
    );
}

function renderFieldValue(field) {
    const value = field.value;
    if (value === null || value === undefined || (Array.isArray(value) && value.length === 0)) {
        return formatValue(value);
    }

    if (field.field_name === 'materials' && Array.isArray(value)) return renderMaterialList(value);
    if (field.field_name === 'components' && Array.isArray(value)) return renderComponentList(value);
    if (field.field_name === 'hazardous_substances' && Array.isArray(value)) return renderHazardList(value);
    if (field.field_name === 'maintenance_schedule' && Array.isArray(value)) return renderScheduleList(value);
    if (field.field_name === 'dimensions' && typeof value === 'object') return renderObjectGrid(value);
    if (field.field_name === 'energy_label' && typeof value === 'object') return renderObjectGrid(value);

    if (Array.isArray(value) && typeof value[0] === 'object') return renderGenericObjectList(value);
    if (Array.isArray(value)) {
        return (
            <div className="chip-list">
                {value.map((item, index) => <span key={`${item}-${index}`} className="data-chip">{formatValue(item)}</span>)}
            </div>
        );
    }
    if (typeof value === 'object') return renderObjectGrid(value);
    return formatValue(value);
}

/* ─── App ──────────────────────────────────────────────────────────────────── */

export default function App() {
    const [view, setView] = useState('home'); // home | passport | raw | registry | builder | mappings | batch
    const [batchIds, setBatchIds] = useState([]);
    const [products, setProducts] = useState([]);
    const [passportData, setPassportData] = useState(null);
    const [rawPassportData, setRawPassportData] = useState(null);
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState(null);
    const [searchId, setSearchId] = useState('');
    const [role, setRole] = useState('consumer');
    const [event, setEvent] = useState('purchase');
    const [roles, setRoles] = useState([]);
    const [events, setEvents] = useState([]);
    const [registryServices, setRegistryServices] = useState([]);
    const [vocabularyTerms, setVocabularyTerms] = useState([]);
    const [dppTemplates, setDppTemplates] = useState([]);
    const [promotedTerms, setPromotedTerms] = useState([]);
    const [lifecyclePhases, setLifecyclePhases] = useState([]);
    const [ontologyMappings, setOntologyMappings] = useState({ mapping_sets: [], mappings: [] });
    const [openCategories, setOpenCategories] = useState({});

    // Load products and ontology on mount
    useEffect(() => {
        loadInitialData();
    }, []);

    async function loadInitialData() {
        try {
            const [productResp, rolesResp, eventsResp] = await Promise.allSettled([
                api.listProducts(),
                api.getRoles(),
                api.getEvents(),
            ]);
            if (productResp.status === 'fulfilled') setProducts(productResp.value.products || []);
            if (rolesResp.status === 'fulfilled') setRoles(rolesResp.value.roles || []);
            if (eventsResp.status === 'fulfilled') setEvents(eventsResp.value.events || []);
        } catch (_e) {
            // Silently handle – services might not be up yet
        }
    }

    async function handleResolve(productId) {
        setLoading(true);
        setError(null);
        try {
            const data = await api.resolveProduct(productId || searchId, role, event);
            setPassportData(data);
            setView('passport');
            // Open all categories by default
            if (data?.recommendation?.recommended_fields) {
                const cats = {};
                data.recommendation.recommended_fields.forEach(f => { cats[f.category] = true; });
                setOpenCategories(cats);
            }
        } catch (e) {
            setError(e.message);
        } finally {
            setLoading(false);
        }
    }

    async function handleRawPassport(productId) {
        setLoading(true);
        setError(null);
        try {
            const data = await api.resolveProductRaw(productId || searchId);
            setRawPassportData(data);
            setView('raw');
        } catch (e) {
            setError(e.message);
        } finally {
            setLoading(false);
        }
    }

    function handleBatchResolve(ids) {
        setBatchIds(ids);
        setView('batch');
    }

    function handleOpenPassportFromBatch(data, productId) {
        setPassportData(data);
        if (data?.recommendation?.recommended_fields) {
            const cats = {};
            data.recommendation.recommended_fields.forEach(f => { cats[f.category] = true; });
            setOpenCategories(cats);
        }
        setView('passport');
    }

    async function loadRegistry() {
        try {
            const services = await api.getRegisteredServices();
            setRegistryServices(services);
        } catch (e) {
            setError(e.message);
        }
        setView('registry');
    }

    async function loadBuilder() {
        setError(null);
        try {
            const [productResp, termsResp, templatesResp, promotedResp, phasesResp] = await Promise.allSettled([
                api.listProducts(),
                api.getVocabularyTerms(),
                api.getDppTemplates(),
                api.getPromotedTemplateTerms(),
                api.getLifecyclePhases(),
            ]);
            if (productResp.status === 'fulfilled') setProducts(productResp.value.products || []);
            if (termsResp.status === 'fulfilled') setVocabularyTerms(termsResp.value.terms || []);
            if (templatesResp.status === 'fulfilled') setDppTemplates(templatesResp.value.templates || []);
            if (promotedResp.status === 'fulfilled') setPromotedTerms(promotedResp.value.terms || []);
            if (phasesResp.status === 'fulfilled') setLifecyclePhases(phasesResp.value.lifecycle_phases || []);
        } catch (e) {
            setError(e.message);
        }
        setView('builder');
    }

    async function loadMappings() {
        setError(null);
        try {
            const data = await api.getOntologyMappings();
            setOntologyMappings({
                mapping_sets: data.mapping_sets || [],
                mappings: data.mappings || [],
            });
        } catch (e) {
            setError(e.message);
        }
        setView('mappings');
    }

    function toggleCategory(cat) {
        setOpenCategories(prev => ({ ...prev, [cat]: !prev[cat] }));
    }

    function groupByCategory(fields) {
        const groups = {};
        fields.forEach(f => {
            if (!groups[f.category]) groups[f.category] = [];
            groups[f.category].push(f);
        });
        return groups;
    }

    // ─── Render ─────────────────────────────────────────────────────────────────

    return (
        <div className="app">
            {/* Header */}
            <header className="app-header">
                <div className="header-content">
                    <a
                        className="header-logo"
                        href="#"
                        onClick={(e) => { e.preventDefault(); setView('home'); setPassportData(null); setError(null); }}
                        aria-label="Digital Product Memory home"
                    >
                        <img src={circthreadLogo} alt="CircThread project logo" />
                    </a>
                    <nav className="header-nav">
                        <button
                            className={`nav-btn ${view === 'home' || view === 'passport' ? 'active' : ''}`}
                            onClick={() => { setView('home'); setPassportData(null); setRawPassportData(null); setError(null); }}
                        >
                            <Search />
                            Passport
                        </button>
                        <button
                            className={`nav-btn ${view === 'registry' ? 'active' : ''}`}
                            onClick={loadRegistry}
                        >
                            <Server />
                            Registry
                        </button>
                        <button
                            className={`nav-btn ${view === 'builder' ? 'active' : ''}`}
                            onClick={loadBuilder}
                        >
                            <ListChecks />
                            DPP Builder
                        </button>
                        <button
                            className={`nav-btn ${view === 'mappings' ? 'active' : ''}`}
                            onClick={loadMappings}
                        >
                            <Waypoints />
                            SSSOM
                        </button>
                    </nav>
                </div>
            </header>

            {/* Content */}
            <main className="app-content">
                {error && (
                    <div className="error-banner">
                        <AlertTriangle />
                        {error}
                    </div>
                )}

                {loading && (
                    <div className="loading-container">
                        <div className="spinner" />
                        <span className="loading-text">Resolving product passport...</span>
                    </div>
                )}

                {!loading && view === 'home' && <HomeView
                    products={products}
                    searchId={searchId}
                    setSearchId={setSearchId}
                    role={role}
                    setRole={setRole}
                    event={event}
                    setEvent={setEvent}
                    roles={roles}
                    events={events}
                    onResolve={handleResolve}
                    onRawPassport={handleRawPassport}
                    onBatchResolve={handleBatchResolve}
                />}

                {view === 'batch' && batchIds.length > 0 && (
                    <BatchOverviewView
                        batchIds={batchIds}
                        role={role}
                        event={event}
                        onBack={() => { setView('home'); setBatchIds([]); }}
                        onOpenPassport={handleOpenPassportFromBatch}
                    />
                )}

                {!loading && view === 'passport' && passportData && <PassportView
                    data={passportData}
                    role={role}
                    event={event}
                    openCategories={openCategories}
                    toggleCategory={toggleCategory}
                    groupByCategory={groupByCategory}
                    onBack={() => { setView('home'); setPassportData(null); }}
                />}

                {!loading && view === 'raw' && rawPassportData && <RawPassportView
                    data={rawPassportData}
                    onBack={() => { setView('home'); setRawPassportData(null); }}
                />}

                {!loading && view === 'registry' && <RegistryView
                    services={registryServices}
                    onRefresh={loadRegistry}
                />}

                {!loading && view === 'builder' && <DppBuilderView
                    products={products}
                    terms={vocabularyTerms}
                    templates={dppTemplates}
                    promotedTerms={promotedTerms}
                    role={role}
                    setRole={setRole}
                    event={event}
                    setEvent={setEvent}
                    roles={roles}
                    events={events}
                    lifecyclePhases={lifecyclePhases}
                    onRefresh={loadBuilder}
                />}

                {!loading && view === 'mappings' && <SssomMappingsView
                    mappingSets={ontologyMappings.mapping_sets}
                    mappings={ontologyMappings.mappings}
                    onRefresh={loadMappings}
                />}
            </main>
        </div>
    );
}

/* ─── QR Scanner Modal ─────────────────────────────────────────────────────── */

function QrScannerModal({ onScan, onClose }) {
    const videoRef = useRef(null);
    const readerRef = useRef(null);
    const controlsRef = useRef(null);
    const [error, setError] = useState(null);
    const [scanning, setScanning] = useState(false);

    const stopScanner = useCallback(() => {
        if (controlsRef.current) {
            try { controlsRef.current.stop(); } catch (_) {}
            controlsRef.current = null;
        }
    }, []);

    useEffect(() => {
        readerRef.current = new BrowserQRCodeReader();
        setScanning(true);
        setError(null);

        BrowserQRCodeReader.listVideoInputDevices()
            .then((devices) => {
                if (!devices || devices.length === 0) {
                    setError('No camera found. Allow camera access and try again.');
                    setScanning(false);
                    return;
                }
                const deviceId = devices[0].deviceId;
                return readerRef.current.decodeFromVideoDevice(
                    deviceId,
                    videoRef.current,
                    (result, err, controls) => {
                        if (!controlsRef.current) controlsRef.current = controls;
                        if (result) {
                            const text = result.getText();
                            try {
                                const data = JSON.parse(text);
                                if (!data.product_id) throw new Error('Missing product_id');
                                stopScanner();
                                onScan(data);
                            } catch (_) {
                                setError(`QR code does not contain valid product data.\nRead: ${text}`);
                            }
                        }
                    }
                );
            })
            .catch((e) => {
                setError(`Camera error: ${e.message}`);
                setScanning(false);
            });

        return () => stopScanner();
    }, [onScan, stopScanner]);

    return (
        <div className="qr-modal-overlay" onClick={onClose}>
            <div className="qr-modal" onClick={(e) => e.stopPropagation()}>
                <div className="qr-modal-header">
                    <div className="qr-modal-title">
                        <QrCode size={18} />
                        Scan QR Code
                    </div>
                    <button className="qr-modal-close" onClick={onClose} aria-label="Close scanner">
                        <X size={18} />
                    </button>
                </div>

                <div className="qr-video-wrapper">
                    <video ref={videoRef} className="qr-video" muted playsInline />
                    {scanning && !error && (
                        <div className="qr-scan-line" />
                    )}
                </div>

                {error ? (
                    <div className="qr-error">
                        <AlertTriangle size={16} />
                        <span style={{ whiteSpace: 'pre-line' }}>{error}</span>
                    </div>
                ) : (
                    <p className="qr-hint">
                        <Camera size={14} />
                        Point the camera at a CircThread QR code
                    </p>
                )}
            </div>
        </div>
    );
}

/* ─── NFC Scanner Modal ─────────────────────────────────────────────────────── */

function NfcScannerModal({ onScan, onClose }) {
    const [status, setStatus] = useState('starting'); // starting | scanning | error
    const [error, setError] = useState('');

    useEffect(() => {
        if (!('NDEFReader' in window)) {
            setError('Web NFC is not supported in this browser.\nUse Chrome on Android to scan NFC tags.');
            setStatus('error');
            return;
        }
        const reader = new window.NDEFReader();

        reader.scan()
            .then(() => setStatus('scanning'))
            .catch((e) => { setError(e.message || 'Could not start NFC reader.'); setStatus('error'); });

        const onReading = ({ message }) => {
            for (const record of message.records) {
                let text = '';
                try {
                    if (record.recordType === 'text') {
                        text = new TextDecoder(record.encoding || 'utf-8').decode(record.data);
                    } else if (record.recordType === 'url') {
                        const raw = new TextDecoder().decode(record.data);
                        try {
                            const u = new URL(raw);
                            const pid = u.searchParams.get('product_id');
                            if (pid) { onScan({ product_id: pid }); return; }
                        } catch (_) {}
                        text = raw;
                    }
                } catch (_) {}
                if (!text) continue;
                try {
                    const data = JSON.parse(text);
                    if (data.product_id) { onScan(data); return; }
                } catch (_) {}
                onScan({ product_id: text.trim() });
                return;
            }
            setError('NFC tag does not contain valid product data.');
        };

        const onReadingError = () =>
            setError('Cannot read NFC tag. Place it closer to your device.');

        reader.addEventListener('reading', onReading);
        reader.addEventListener('readingerror', onReadingError);
        return () => {
            reader.removeEventListener('reading', onReading);
            reader.removeEventListener('readingerror', onReadingError);
        };
    }, [onScan]);

    return (
        <div className="qr-modal-overlay" onClick={onClose}>
            <div className="qr-modal" onClick={(e) => e.stopPropagation()}>
                <div className="qr-modal-header">
                    <div className="qr-modal-title"><Wifi size={18} /> Scan NFC Tag</div>
                    <button className="qr-modal-close" onClick={onClose} aria-label="Close scanner"><X size={18} /></button>
                </div>
                <div className="nfc-scan-area">
                    {status === 'error'
                        ? <AlertTriangle size={48} style={{ color: '#d93025' }} />
                        : <div className={`nfc-pulse-ring${status === 'scanning' ? ' nfc-active' : ''}`}><Wifi size={40} /></div>
                    }
                </div>
                {error
                    ? <div className="qr-error"><AlertTriangle size={16} /><span style={{ whiteSpace: 'pre-line' }}>{error}</span></div>
                    : <p className="qr-hint"><Wifi size={14} />{status === 'starting' ? 'Starting NFC reader…' : 'Hold a CircThread NFC tag near your device'}</p>
                }
            </div>
        </div>
    );
}

/* ─── RFID Scanner Modal ─────────────────────────────────────────────────────── */

function RfidScannerModal({ batchMode, onScan, onBatchComplete, onClose }) {
    const [buffer, setBuffer] = useState('');
    const [batchList, setBatchList] = useState([]);
    const [lastScan, setLastScan] = useState('');
    const inputRef = useRef(null);

    // Keep focus on the hidden input so keyboard-emulation RFID readers are captured
    useEffect(() => {
        inputRef.current?.focus();
        const id = setInterval(() => {
            if (document.activeElement !== inputRef.current) inputRef.current?.focus();
        }, 400);
        return () => clearInterval(id);
    }, []);

    const processInput = useCallback((raw) => {
        const text = raw.trim();
        if (!text) return;
        let data;
        try {
            data = JSON.parse(text);
            if (!data.product_id) data = { product_id: text };
        } catch (_) {
            data = { product_id: text };
        }
        if (!batchMode) { onScan(data); return; }
        setLastScan(data.product_id);
        setBatchList(prev => prev.includes(data.product_id) ? prev : [...prev, data.product_id]);
    }, [batchMode, onScan]);

    const handleKeyDown = (e) => {
        if (e.key === 'Enter' || e.key === 'Tab') {
            e.preventDefault();
            processInput(buffer);
            setBuffer('');
        }
    };

    return (
        <div className="qr-modal-overlay" onClick={onClose}>
            <div className={`rfid-modal qr-modal${batchMode ? ' rfid-batch' : ''}`} onClick={(e) => e.stopPropagation()}>
                <div className="qr-modal-header">
                    <div className="qr-modal-title">
                        <Radio size={18} />
                        {batchMode ? 'RFID Batch Scan' : 'Scan RFID Tag'}
                    </div>
                    <button className="qr-modal-close" onClick={onClose} aria-label="Close scanner"><X size={18} /></button>
                </div>

                {/* Hidden input captures keyboard-emulation output from USB RFID readers */}
                <input
                    ref={inputRef}
                    className="rfid-hidden-input"
                    value={buffer}
                    onChange={(e) => setBuffer(e.target.value)}
                    onKeyDown={handleKeyDown}
                    aria-label="RFID tag input"
                    autoComplete="off"
                />

                <div className="rfid-scan-area">
                    <div className={`rfid-pulse-ring${lastScan ? ' rfid-success' : ''}`}>
                        <Radio size={36} />
                    </div>
                    <p className="rfid-status-text">
                        {lastScan
                            ? <><CheckSquare size={14} style={{ color: 'var(--accent)', verticalAlign: 'middle', marginRight: 4 }} />Scanned: <strong>{lastScan}</strong></>
                            : 'Hold an RFID tag near the reader…'
                        }
                    </p>
                </div>

                {batchMode && (
                    <div className="rfid-batch-section">
                        {batchList.length === 0 ? (
                            <p className="rfid-batch-empty">No tags scanned yet. Scan tags one by one.</p>
                        ) : (
                            <>
                                <div className="rfid-batch-header">
                                    <span>{batchList.length} product{batchList.length !== 1 ? 's' : ''} scanned</span>
                                    <button className="rfid-clear-btn" onClick={() => { setBatchList([]); setLastScan(''); }}>Clear all</button>
                                </div>
                                <ul className="rfid-batch-items">
                                    {batchList.map(id => (
                                        <li key={id} className="rfid-batch-item">
                                            <span className="rfid-batch-id">{id}</span>
                                            <button
                                                className="rfid-remove-btn"
                                                onClick={() => setBatchList(p => p.filter(x => x !== id))}
                                                aria-label={`Remove ${id}`}
                                            >
                                                <X size={12} />
                                            </button>
                                        </li>
                                    ))}
                                </ul>
                                <button className="rfid-resolve-btn" onClick={() => onBatchComplete(batchList)}>
                                    View DPP Overview — {batchList.length} product{batchList.length !== 1 ? 's' : ''}
                                </button>
                            </>
                        )}
                    </div>
                )}

                <p className="qr-hint">
                    <Radio size={14} />
                    {batchMode
                        ? 'Keep scanning. Each RFID tag is added to the list above.'
                        : 'USB RFID readers work in keyboard-emulation mode — no driver needed.'
                    }
                </p>
            </div>
        </div>
    );
}

/* ─── Batch DPP Overview ────────────────────────────────────────────────────── */

function BatchOverviewView({ batchIds, role, event, onBack, onOpenPassport }) {
    const [results, setResults] = useState([]);
    const [resolved, setResolved] = useState(0);
    const [done, setDone] = useState(false);

    useEffect(() => {
        let cancelled = false;
        setResults([]);
        setResolved(0);
        setDone(false);

        (async () => {
            const out = [];
            for (const id of batchIds) {
                if (cancelled) return;
                try {
                    const data = await api.resolveProduct(id, role, event);
                    out.push({ product_id: id, data, error: null });
                } catch (e) {
                    out.push({ product_id: id, data: null, error: e.message });
                }
                if (!cancelled) { setResults([...out]); setResolved(out.length); }
            }
            if (!cancelled) setDone(true);
        })();

        return () => { cancelled = true; };
    }, [batchIds, role, event]);

    const progress = batchIds.length ? (resolved / batchIds.length) * 100 : 0;
    const loading = !done;

    return (
        <div className="batch-overview">
            <div className="batch-overview-top">
                <button className="back-btn" onClick={onBack}><ArrowLeft /> Back to Search</button>
                <div className="batch-overview-meta">
                    <LayoutGrid size={20} />
                    <h2 className="batch-overview-title">RFID Batch Overview</h2>
                    <span className="batch-count-badge">{batchIds.length} products</span>
                    {role && <span className="context-chip"><User size={11} /> {role}</span>}
                    {event && <span className="context-chip"><Calendar size={11} /> {event}</span>}
                </div>
            </div>

            {loading && (
                <div className="batch-progress-wrap">
                    <div className="batch-progress-outer">
                        <div className="batch-progress-inner" style={{ width: `${progress}%` }} />
                    </div>
                    <span className="batch-progress-label">Resolving {resolved} / {batchIds.length}…</span>
                </div>
            )}

            <div className="batch-grid">
                {results.map(({ product_id, data, error }) => {
                    const passport = data?.passport || {};
                    const rec = data?.recommendation;
                    const topFields = (rec?.recommended_fields || [])
                        .filter(f => f.value !== null && f.value !== undefined && f.value !== '')
                        .slice(0, 4);

                    return (
                        <div key={product_id} className={`batch-card${error ? ' batch-card-error' : ''}`}>
                            <div className="batch-card-head">
                                <span className="batch-card-type">
                                    {PRODUCT_TYPE_LABELS[data?.product_type] || data?.product_type || '—'}
                                </span>
                                <span className="batch-card-pid">{product_id}</span>
                            </div>

                            {error ? (
                                <div className="batch-card-err"><AlertTriangle size={16} /><span>{error}</span></div>
                            ) : (
                                <>
                                    <h3 className="batch-card-model">
                                        {passport.model || passport.manufacturer || product_id}
                                    </h3>
                                    {passport.manufacturer && <div className="batch-card-mfr">{passport.manufacturer}</div>}

                                    {topFields.length > 0 && (
                                        <ul className="batch-card-fields">
                                            {topFields.map(f => (
                                                <li key={f.field_name}>
                                                    <span className="bcf-name">{f.display_name}</span>
                                                    <span className="bcf-value">
                                                        {Array.isArray(f.value)
                                                            ? `${f.value.length} item${f.value.length !== 1 ? 's' : ''}`
                                                            : typeof f.value === 'object'
                                                                ? JSON.stringify(f.value).slice(0, 40)
                                                                : String(f.value).slice(0, 60)
                                                        }
                                                    </span>
                                                </li>
                                            ))}
                                        </ul>
                                    )}

                                    {rec && (
                                        <div className="batch-card-foot">
                                            <span className="batch-fields-count">{rec.fields_shown}/{rec.total_fields_available} fields</span>
                                            {rec.filter_mode && (
                                                <span className="batch-mode-badge">{rec.filter_mode.replace('_', '+')}</span>
                                            )}
                                        </div>
                                    )}

                                    <button className="batch-open-btn" onClick={() => onOpenPassport(data, product_id)}>
                                        Open Full Passport
                                    </button>
                                </>
                            )}
                        </div>
                    );
                })}

                {loading && Array.from({ length: batchIds.length - results.length }).map((_, i) => (
                    <div key={`ph-${i}`} className="batch-card batch-card-loading">
                        <div className="batch-skeleton" />
                        <div className="batch-skeleton batch-skeleton-sm" />
                        <div className="batch-skeleton batch-skeleton-xs" />
                    </div>
                ))}
            </div>
        </div>
    );
}

/* ─── Home View ────────────────────────────────────────────────────────────── */

function HomeView({ products, searchId, setSearchId, role, setRole, event, setEvent, roles, events, onResolve, onRawPassport, onBatchResolve }) {
    const [showScanner, setShowScanner] = useState(false);
    const [showNfcScanner, setShowNfcScanner] = useState(false);
    const [showRfidScanner, setShowRfidScanner] = useState(false);
    const [rfidBatchMode, setRfidBatchMode] = useState(false);

    const applyScannedData = useCallback((data, closeAll) => {
        closeAll();
        if (data.product_id) setSearchId(data.product_id);
        if (data.role)       setRole(data.role);
        if (data.event)      setEvent(data.event);
        setTimeout(() => onResolve(data.product_id), 50);
    }, [setSearchId, setRole, setEvent, onResolve]);

    const handleScan = useCallback((data) => {
        applyScannedData(data, () => setShowScanner(false));
    }, [applyScannedData]);

    const handleNfcScan = useCallback((data) => {
        applyScannedData(data, () => setShowNfcScanner(false));
    }, [applyScannedData]);

    const handleRfidScan = useCallback((data) => {
        applyScannedData(data, () => setShowRfidScanner(false));
    }, [applyScannedData]);

    const handleRfidBatchComplete = useCallback((ids) => {
        setShowRfidScanner(false);
        onBatchResolve(ids);
    }, [onBatchResolve]);

    return (
        <div>
            {showScanner && (
                <QrScannerModal onScan={handleScan} onClose={() => setShowScanner(false)} />
            )}
            {showNfcScanner && (
                <NfcScannerModal onScan={handleNfcScan} onClose={() => setShowNfcScanner(false)} />
            )}
            {showRfidScanner && (
                <RfidScannerModal
                    batchMode={rfidBatchMode}
                    onScan={handleRfidScan}
                    onBatchComplete={handleRfidBatchComplete}
                    onClose={() => setShowRfidScanner(false)}
                />
            )}
            <div className="search-hero">
                <h1>Digital Product Passport</h1>
                <p>
                    Discover role-specific product lifecycle data powered by a
                    decentralised knowledge graph.
                </p>

                <div className="search-container">
                    <div className="search-input-wrapper">
                        <Search />
                        <input
                            className="search-input"
                            type="text"
                            placeholder="Enter product ID or model identifier (e.g. SN43HW04ME)"
                            value={searchId}
                            onChange={(e) => setSearchId(e.target.value)}
                            onKeyDown={(e) => e.key === 'Enter' && onResolve()}
                        />
                    </div>
                    <button
                        className="qr-scan-btn"
                        onClick={() => setShowScanner(true)}
                        title="Scan QR code"
                        aria-label="Scan QR code"
                    >
                        <QrCode size={18} />
                    </button>
                    <button
                        className="qr-scan-btn"
                        onClick={() => setShowNfcScanner(true)}
                        title="Scan NFC tag (Chrome on Android)"
                        aria-label="Scan NFC tag"
                    >
                        <Wifi size={18} />
                    </button>
                    <button
                        className="qr-scan-btn"
                        onClick={() => { setRfidBatchMode(false); setShowRfidScanner(true); }}
                        title="Scan RFID tag"
                        aria-label="Scan RFID tag"
                    >
                        <Radio size={18} />
                    </button>
                    <button
                        className="qr-scan-btn rfid-batch-btn"
                        onClick={() => { setRfidBatchMode(true); setShowRfidScanner(true); }}
                        title="RFID batch scan — scan multiple products and view all DPPs at once"
                        aria-label="RFID batch scan"
                    >
                        <LayoutGrid size={18} />
                    </button>
                    <button className="search-btn" onClick={() => onResolve()}>
                        Resolve
                    </button>
                    <button className="secondary-search-btn" onClick={() => onRawPassport()}>
                        Show all data
                    </button>
                </div>

                <div className="filters-bar">
                    <div className="filter-group">
                        <label className="filter-label">Stakeholder Role</label>
                        <select className="filter-select" value={role} onChange={(e) => setRole(e.target.value)}>
                            <option value="">Any role</option>
                            {roles.length > 0
                                ? roles.map(r => <option key={r.name} value={r.name}>{r.display_name}</option>)
                                : <>
                                    <option value="consumer">End Consumer</option>
                                    <option value="recycler">Recycling Company</option>
                                    <option value="manufacturer">Product Manufacturer</option>
                                    <option value="repairer">Repair Service Provider</option>
                                    <option value="collector">Collection & B-Stock Operator</option>
                                </>
                            }
                        </select>
                        <p className="filter-help">Use a specific role for the most precise recommendation, or Any role to aggregate across stakeholders.</p>
                    </div>
                    <div className="filter-group">
                        <label className="filter-label">Lifecycle Event</label>
                        <select className="filter-select" value={event} onChange={(e) => setEvent(e.target.value)}>
                            <option value="">Any event</option>
                            {events.length > 0
                                ? events.map(ev => <option key={ev.name} value={ev.name}>{ev.display_name}</option>)
                                : <>
                                    <option value="purchase">Product Purchase</option>
                                    <option value="repair">Product Repair</option>
                                    <option value="recycling">End-of-Life Recycling</option>
                                    <option value="maintenance">Scheduled Maintenance</option>
                                    <option value="disposal">Product Disposal</option>
                                    <option value="resale">Second-hand Resale</option>
                                </>
                            }
                        </select>
                        <p className="filter-help">Use a specific lifecycle event for context, or Any event to aggregate across situations.</p>
                    </div>
                </div>
                <div className="context-explainer">
                    <Info />
                    <span>
                        Role + event is the primary mode. If one filter is set to Any, the Knowledge Graph aggregates matching recommendations with the highest available priority.
                    </span>
                </div>
            </div>

            <section className="help-panel" aria-label="How to use Digital Product Memory">
                <div className="help-panel-header">
                    <h2>How to resolve a passport</h2>
                    <p>Select the user context first. The software then filters the product passport to the fields that matter for that situation.</p>
                </div>
                <div className="workflow-grid">
                    <div className="workflow-step">
                        <div className="workflow-icon"><Search /></div>
                        <h3>1. Choose a product</h3>
                        <p>Enter a product ID or pick one of the available prototype products below.</p>
                    </div>
                    <div className="workflow-step">
                        <div className="workflow-icon"><User /></div>
                        <h3>2. Set role and event</h3>
                        <p>The role and lifecycle event decide which passport fields are relevant.</p>
                    </div>
                    <div className="workflow-step">
                        <div className="workflow-icon"><Database /></div>
                        <h3>3. Review the result</h3>
                        <p>The Resolver fetches provider data and the Knowledge Graph ranks the visible fields.</p>
                    </div>
                </div>
            </section>

            {products.length > 0 && (
                <>
                    <h2 style={{ fontWeight: 600, color: '#6e6e73', marginBottom: 12, textTransform: 'uppercase', letterSpacing: '0.06em', fontSize: 11 }}>
                        Available Products
                    </h2>
                    <div className="products-grid">
                        {products.map(p => (
                            <div key={p.product_id} className="product-card" onClick={() => { setSearchId(p.product_id); onResolve(p.product_id); }}>
                                <div className="product-card-type">
                                    <Zap />
                                    {PRODUCT_TYPE_LABELS[p.product_type] || p.product_type}
                                </div>
                                <h3>{p.model}</h3>
                                <div className="manufacturer">{p.manufacturer}</div>
                                <div className="product-card-meta">
                                    <span className="meta-badge">
                                        <Info />
                                        {p.product_id}
                                    </span>
                                </div>
                                <div className="product-card-actions" onClick={(e) => e.stopPropagation()}>
                                    <button type="button" onClick={() => { setSearchId(p.product_id); onResolve(p.product_id); }}>
                                        Recommended view
                                    </button>
                                    <button type="button" onClick={() => { setSearchId(p.product_id); onRawPassport(p.product_id); }}>
                                        All data
                                    </button>
                                </div>
                            </div>
                        ))}
                    </div>
                </>
            )}
        </div>
    );
}

/* ─── Passport View ────────────────────────────────────────────────────────── */

function isMissingValue(value) {
    if (value === null || value === undefined) return true;
    if (typeof value === 'string' && value.trim() === '') return true;
    if (Array.isArray(value) && value.length === 0) return true;
    return false;
}

function PassportView({ data, role, event, openCategories, toggleCategory, groupByCategory, onBack }) {
    const [missingExpanded, setMissingExpanded] = useState(false);
    const [suggestionsExpanded, setSuggestionsExpanded] = useState(false);
    const [providersExpanded, setProvidersExpanded] = useState(false);
    const rec = data.recommendation;
    const fields = rec?.recommended_fields || [];
    const suggestions = rec?.suggested_fields || [];
    const selection = data.provider_selection;
    const conflicts = Object.keys(data.conflicts || {});
    const grouped = groupByCategory(fields);
    const selectedRole = rec?.role ?? data.role ?? role;
    const selectedEvent = rec?.event ?? data.event ?? event;
    const filterMode = rec?.filter_mode || 'role_event';
    const missingFields = fields.filter(f => isMissingValue(f.value));

    return (
        <div className="passport-view">
            <button className="back-btn" onClick={onBack}>
                <ArrowLeft /> Back to Search
            </button>

            <div className="passport-header">
                <div className="passport-header-info">
                    <h2>{data.passport?.model || data.passport?.manufacturer || data.product_id}</h2>
                    <div className="subtitle">
                        {data.passport?.manufacturer && `${data.passport.manufacturer} · `}
                        {PRODUCT_TYPE_LABELS[data.product_type] || data.product_type}
                        {data.passport?.serial_number && ` · ${data.passport.serial_number}`}
                    </div>
                </div>
                <div className="passport-context">
                    <span className="context-badge role">
                        <User />
                        {contextLabel(selectedRole, 'Any role')}
                    </span>
                    <span className="context-badge event">
                        <Calendar />
                        {contextLabel(selectedEvent, 'Any event')}
                    </span>
                    <span className="context-badge mode">
                        <Zap />
                        {recommendationModeLabel(filterMode)}
                    </span>
                </div>
            </div>

            {rec && (
                <div className="passport-stats">
                    <div className="stat-card">
                        <div className="stat-value">{rec.fields_shown}</div>
                        <div className="stat-label">Fields shown</div>
                    </div>
                    <div className="stat-card">
                        <div className="stat-value">{rec.total_fields_available}</div>
                        <div className="stat-label">Total available</div>
                    </div>
                    <div className="stat-card">
                        <div className="stat-value">{rec.total_fields_available > 0 ? Math.round((rec.fields_shown / rec.total_fields_available) * 100) : 0}%</div>
                        <div className="stat-label">Data reduction</div>
                    </div>
                    <div className="stat-card">
                        <div className="stat-value">{data.sources?.length || 0}</div>
                        <div className="stat-label">Data sources</div>
                    </div>
                    <div className="stat-card">
                        <div className="stat-value">{recommendationModeLabel(filterMode)}</div>
                        <div className="stat-label">Filter mode</div>
                    </div>
                </div>
            )}

            {missingFields.length > 0 && (
                <div className="missing-fields-banner">
                    <div className="missing-fields-header" onClick={() => setMissingExpanded(v => !v)}>
                        <div className="missing-fields-title">
                            <AlertTriangle />
                            <strong>{missingFields.length} recommended field{missingFields.length !== 1 ? 's' : ''} missing data from providers</strong>
                        </div>
                        <span className="missing-fields-toggle">
                            {missingExpanded ? 'Hide' : 'Show details'}
                            <ChevronDown style={{ transform: missingExpanded ? 'rotate(180deg)' : 'none', transition: 'transform 0.2s' }} />
                        </span>
                    </div>
                    {missingExpanded && (
                        <div className="missing-fields-list">
                            {missingFields.map(f => (
                                <div key={f.field_name} className="missing-field-item">
                                    <span className={`field-priority ${priorityClass(f.priority || 0)}`}>{Math.round((f.priority || 0) * 100)}</span>
                                    <span className="missing-field-name">{f.display_name}</span>
                                    <span className="missing-field-category">{CATEGORY_DISPLAY[f.category] || f.category}</span>
                                </div>
                            ))}
                        </div>
                    )}
                </div>
            )}

            <div className="categories-grid">
                {Object.entries(grouped).map(([category, catFields]) => {
                    const Icon = CATEGORY_ICONS[category] || Info;
                    const isOpen = openCategories[category];

                    return (
                        <div key={category} className="category-section">
                            <div className="category-header" onClick={() => toggleCategory(category)}>
                                <div className="category-header-left">
                                    <div className={`category-icon ${category}`}>
                                        <Icon />
                                    </div>
                                    <div>
                                        <h3>{CATEGORY_DISPLAY[category] || category}</h3>
                                        <span className="field-count">{catFields.length} field{catFields.length !== 1 ? 's' : ''}</span>
                                    </div>
                                </div>
                                <div className={`category-toggle ${isOpen ? 'open' : ''}`}>
                                    <ChevronDown />
                                </div>
                            </div>

                            {isOpen && (
                                <div className="category-content">
                                    {catFields
                                        .sort((a, b) => (b.priority || 0) - (a.priority || 0))
                                        .map(field => (
                                            <div key={field.field_name} className={`field-row${isMissingValue(field.value) ? ' field-row--missing' : ''}`}>
                                                <span className={`field-priority ${priorityClass(field.priority || 0)}`}>
                                                    {Math.round((field.priority || 0) * 100)}
                                                </span>
                                                <div className="field-info">
                                                    <div className="field-name-row">
                                                        <div className="field-name">{field.display_name}</div>
                                                        <div style={{ display: 'flex', gap: '6px', alignItems: 'center' }}>
                                                            {isMissingValue(field.value) && (
                                                                <span className="missing-value-badge"><AlertTriangle /> No data</span>
                                                            )}
                                                            <span className="priority-label">{recommendationModeLabel(field.filter_mode || filterMode)}</span>
                                                        </div>
                                                    </div>
                                                    {((field.matched_roles?.length || 0) > 0 || (field.matched_events?.length || 0) > 0) && (
                                                        <div className="field-sources">
                                                            {(field.matched_roles || []).map(item => <span key={`role-${field.field_name}-${item}`} className="source-badge"><User /> {item}</span>)}
                                                            {(field.matched_events || []).map(item => <span key={`event-${field.field_name}-${item}`} className="source-badge"><Calendar /> {item}</span>)}
                                                        </div>
                                                    )}
                                                    {field.sources?.length > 0 && (
                                                        <div className="field-sources">
                                                            {field.sources.map(source => (
                                                                <span key={source} className="source-badge">
                                                                    <Server /> {source}
                                                                </span>
                                                            ))}
                                                        </div>
                                                    )}
                                                    <div className="field-value">
                                                        {renderFieldValue(field)}
                                                    </div>
                                                </div>
                                            </div>
                                        ))
                                    }
                                </div>
                            )}
                        </div>
                    );
                })}
            </div>

            {rec?.fallback === 'role' && (
                <div className="info-banner">
                    <Info /> No relevance profile is modelled for this role–event combination. The view shows the role's recommendations across all lifecycle events.
                </div>
            )}

            {suggestions.length > 0 && (
                <div className="missing-fields-banner suggestions-banner">
                    <div className="missing-fields-header" onClick={() => setSuggestionsExpanded(v => !v)}>
                        <div className="missing-fields-title">
                            <Zap />
                            <strong>{suggestions.length} further suggestion{suggestions.length !== 1 ? 's' : ''} from the extended algorithms (not part of this role-specific view)</strong>
                        </div>
                        <span className="missing-fields-toggle">
                            {suggestionsExpanded ? 'Hide' : 'Show'}
                            <ChevronDown style={{ transform: suggestionsExpanded ? 'rotate(180deg)' : 'none', transition: 'transform 0.2s' }} />
                        </span>
                    </div>
                    {suggestionsExpanded && (
                        <div className="missing-fields-list">
                            {suggestions.map(f => (
                                <div key={f.field_name} className="missing-field-item">
                                    <span className={`field-priority ${priorityClass(f.priority || 0)}`}>{Math.round((f.priority || 0) * 100)}</span>
                                    <span className="missing-field-name">{f.display_name}</span>
                                    <span className="missing-field-category">{f.recommendation_source}</span>
                                    <span className="missing-field-category">{isMissingValue(f.value) ? 'no data' : 'data available'}</span>
                                </div>
                            ))}
                        </div>
                    )}
                </div>
            )}

            {selection && (
                <div className="missing-fields-banner providers-banner">
                    <div className="missing-fields-header" onClick={() => setProvidersExpanded(v => !v)}>
                        <div className="missing-fields-title">
                            <Server />
                            <strong>
                                {selection.queried?.length || 0} provider{(selection.queried?.length || 0) !== 1 ? 's' : ''} queried, {selection.excluded?.length || 0} skipped
                                {selection.unavailable?.length > 0 ? ` · ${selection.unavailable.length} unavailable` : ''}
                                {conflicts.length > 0 ? ` · ${conflicts.length} conflicting field${conflicts.length !== 1 ? 's' : ''}` : ''}
                            </strong>
                        </div>
                        <span className="missing-fields-toggle">
                            {providersExpanded ? 'Hide' : 'Show details'}
                            <ChevronDown style={{ transform: providersExpanded ? 'rotate(180deg)' : 'none', transition: 'transform 0.2s' }} />
                        </span>
                    </div>
                    {providersExpanded && (
                        <div className="missing-fields-list">
                            {(selection.queried || []).map(name => (
                                <div key={`q-${name}`} className="missing-field-item">
                                    <span className="missing-field-name">{name}</span>
                                    <span className="missing-field-category">{(selection.responded || []).includes(name)
                                        ? 'queried · data returned'
                                        : (selection.unavailable || []).some(u => u.name === name)
                                            ? `queried · unavailable (${(selection.unavailable || []).find(u => u.name === name).reason})`
                                            : 'queried · no data'}</span>
                                </div>
                            ))}
                            {(selection.excluded || []).map(item => (
                                <div key={`x-${item.name}`} className="missing-field-item">
                                    <span className="missing-field-name">{item.name}</span>
                                    <span className="missing-field-category">skipped · {item.reason}</span>
                                </div>
                            ))}
                            {conflicts.map(field => (
                                <div key={`c-${field}`} className="missing-field-item">
                                    <span className="missing-field-name">{field}</span>
                                    <span className="missing-field-category">conflicting values · {(data.conflicts[field] || []).map(c => c.provider).join(', ')}</span>
                                </div>
                            ))}
                        </div>
                    )}
                </div>
            )}

            {fields.length === 0 && !data.error && (
                <div className="empty-state">
                    <Info />
                    <h3>No data fields recommended</h3>
                    <p>The Knowledge Graph has no mapping for this role-event combination.</p>
                </div>
            )}

            {data.error && (
                <div className="empty-state">
                    <AlertTriangle />
                    <h3>{data.error_reason === 'providers_unavailable' ? 'Product data unavailable' : 'Product not found'}</h3>
                    <p>{data.error}</p>
                </div>
            )}
        </div>
    );
}

/* ─── Registry View ────────────────────────────────────────────────────────── */

function RawPassportView({ data, onBack }) {
    const raw = data.raw_data || {};
    const fieldSources = raw._field_sources || {};
    const fields = Object.entries(raw)
        .filter(([key, value]) => !key.startsWith('_') && value !== null && value !== undefined && value !== '' && !(Array.isArray(value) && value.length === 0))
        .map(([fieldName, value]) => ({
            field_name: fieldName,
            display_name: prettifyKey(fieldName),
            value,
            sources: fieldSources[fieldName] || [],
        }));

    return (
        <div className="passport-view">
            <button className="back-btn" onClick={onBack}>
                <ArrowLeft /> Back to Search
            </button>
            <div className="passport-header">
                <div className="passport-header-info">
                    <h2>{raw.model || raw.manufacturer || data.product_id}</h2>
                    <div className="subtitle">
                        Complete aggregated Digital Product Passport
                        {raw.product_type && ` · ${PRODUCT_TYPE_LABELS[raw.product_type] || raw.product_type}`}
                    </div>
                </div>
                <div className="passport-context">
                    <span className="context-badge role"><Database />{fields.length} fields</span>
                    <span className="context-badge event"><Server />{data.sources?.length || 0} sources</span>
                </div>
            </div>
            <div className="raw-explainer">
                <Info />
                <span>This view shows all data points found by the Resolver across registered providers. No stakeholder role, lifecycle event, or Knowledge Graph filtering is applied.</span>
            </div>
            <div className="categories-grid">
                {fields.map(field => (
                    <div key={field.field_name} className="field-row raw-field-row">
                        <span className="field-priority high">ALL</span>
                        <div className="field-info">
                            <div className="field-name-row">
                                <div className="field-name">{field.display_name}</div>
                                <span className="priority-label">Unfiltered data</span>
                            </div>
                            {field.sources?.length > 0 && (
                                <div className="field-sources">
                                    {field.sources.map(source => <span key={source} className="source-badge"><Server /> {source}</span>)}
                                </div>
                            )}
                            <div className="field-value">{renderFieldValue(field)}</div>
                        </div>
                    </div>
                ))}
            </div>
        </div>
    );
}

function DppBuilderView({ products, terms, templates, promotedTerms, role, setRole, event, setEvent, roles, events, lifecyclePhases, onRefresh }) {
    const [productId, setProductId] = useState(products[0]?.product_id || '');
    const [templateName, setTemplateName] = useState('Custom DPP Template');
    const [customEvent, setCustomEvent] = useState('');
    const [lifecyclePhase, setLifecyclePhase] = useState('');
    const [selectedTerms, setSelectedTerms] = useState([]);
    const [termFilter, setTermFilter] = useState('');
    const [result, setResult] = useState(null);
    const [localLoading, setLocalLoading] = useState(false);
    const [localMessage, setLocalMessage] = useState(null);
    const [editingTemplateId, setEditingTemplateId] = useState(null);

    useEffect(() => {
        if (!productId && products[0]?.product_id) setProductId(products[0].product_id);
    }, [products, productId]);

    const termsByCategory = terms
        .filter(term => `${term.field_name} ${term.display_name} ${term.description || ''}`.toLowerCase().includes(termFilter.toLowerCase()))
        .reduce((groups, term) => {
            const category = term.category || 'other';
            if (!groups[category]) groups[category] = [];
            groups[category].push(term);
            return groups;
        }, {});
    const termMetadata = terms.reduce((acc, term) => ({ ...acc, [term.field_name]: term }), {});
    // A predefined event determines the lifecycle phase; without one, the phase can be chosen freely.
    const derivedPhase = event ? (lifecyclePhases.find(phase => (phase.events || []).includes(event))?.name || '') : '';
    const effectivePhase = event ? derivedPhase : lifecyclePhase;
    const phaseLabel = (name) => lifecyclePhases.find(phase => phase.name === name)?.display_name || prettifyKey(name || '');
    const roleLabel = (name) => roles.find(r => r.name === name)?.display_name || name;
    const eventLabel = (name) => events.find(ev => ev.name === name)?.display_name || name;
    const selectedProduct = products.find(product => product.product_id === productId);

    function toggleTerm(termName) {
        setSelectedTerms(prev => prev.includes(termName) ? prev.filter(t => t !== termName) : [...prev, termName].sort());
    }

    function selectPromoted() {
        setSelectedTerms(prev => Array.from(new Set([...prev, ...promotedTerms.map(t => t.field_name)])).sort());
    }

    function editTemplate(template) {
        setEditingTemplateId(template.template_id);
        setTemplateName(template.template_name || 'Custom DPP Template');
        setSelectedTerms([...(template.terms || [])].sort());
        setRole(template.role || '');
        setEvent(template.event || '');
        setCustomEvent(template.custom_event || '');
        setLifecyclePhase(template.lifecycle_phase || '');
        // Preview a product of the template's product type, so that saving keeps that type.
        setProductId(template.product_type
            ? (products.find(product => product.product_type === template.product_type)?.product_id || '')
            : '');
        setLocalMessage({ type: 'success', text: 'Template loaded for editing. Change terms and save.' });
    }

    function resetTemplateForm() {
        setEditingTemplateId(null);
        setTemplateName('Custom DPP Template');
        setCustomEvent('');
        setLifecyclePhase('');
        setSelectedTerms([]);
        setResult(null);
    }

    async function deleteTemplate(templateId) {
        setLocalLoading(true);
        setLocalMessage(null);
        try {
            await api.deleteDppTemplate(templateId);
            if (editingTemplateId === templateId) resetTemplateForm();
            setLocalMessage({ type: 'success', text: 'Template deleted.' });
            await onRefresh();
        } catch (e) {
            setLocalMessage({ type: 'error', text: e.message });
        } finally {
            setLocalLoading(false);
        }
    }

    async function handleBuild(e) {
        e.preventDefault();
        setLocalMessage(null);
        setResult(null);
        if (selectedTerms.length === 0) {
            setLocalMessage({ type: 'error', text: 'Select at least one vocabulary term.' });
            return;
        }
        setLocalLoading(true);
        // Template context: predefined role/event, a self-defined event name and the
        // lifecycle phase (derived by the backend when a predefined event is selected).
        const context = {
            role: role || null,
            event: event || null,
            custom_event: customEvent.trim() || null,
            lifecycle_phase: event ? null : (lifecyclePhase || null),
        };
        try {
            let data;
            if (editingTemplateId) {
                await api.updateDppTemplate(editingTemplateId, {
                    template_name: templateName,
                    terms: selectedTerms,
                    ...context,
                    // Only change the stored product type when a product is selected for preview.
                    ...(selectedProduct ? { product_type: selectedProduct.product_type } : {}),
                });
                data = await api.buildCustomDpp({
                    product_id: productId || null,
                    template_name: templateName,
                    terms: selectedTerms,
                    ...context,
                    save_template: false,
                });
            } else {
                data = await api.buildCustomDpp({
                    product_id: productId || null,
                    template_name: templateName,
                    terms: selectedTerms,
                    ...context,
                    save_template: true,
                });
            }
            setResult(data);
            setLocalMessage({ type: 'success', text: productId ? (editingTemplateId ? 'Template updated and preview values resolved.' : 'Template saved and preview values resolved through the Resolver.') : 'Template saved without product value preview.' });
            setEditingTemplateId(null);
            await onRefresh();
        } catch (e) {
            setLocalMessage({ type: 'error', text: e.message });
        } finally {
            setLocalLoading(false);
        }
    }

    const resultFields = (result?.selected_fields || []).map(field => ({
        ...field,
        ...(termMetadata[field.field_name] || {}),
        display_name: termMetadata[field.field_name]?.display_name || field.field_name,
        category: termMetadata[field.field_name]?.category || 'selected',
    }));

    return (
        <div className="builder-view">
            <div className="builder-header">
                <div>
                    <h2>DPP Builder</h2>
                    <p>Build a reusable DPP template from Digital Product Memory vocabulary terms. The template itself is product-independent; selecting a product only resolves a value preview through the Resolver.</p>
                </div>
                <button className="back-btn" onClick={onRefresh} style={{ marginBottom: 0 }}><RefreshCw /> Refresh</button>
            </div>
            <section className="builder-explainer">
                <div>
                    <h3>Static and dynamic recommendation graph</h3>
                    <p>The static graph gives cold-start recommendations. Custom templates are stored as dynamic observations. A term becomes an additional recommendation only after it appears in at least two different templates.</p>
                </div>
                <div className="builder-threshold"><strong>{promotedTerms.length}</strong><span>terms above threshold</span></div>
            </section>
            {localMessage && <div className={`registry-message ${localMessage.type}`}>{localMessage.type === 'error' ? <AlertTriangle /> : <Info />}<span>{localMessage.text}</span></div>}
            <form className="builder-layout" onSubmit={handleBuild}>
                <div className="builder-config">
                    <label>Template name<input value={templateName} onChange={(e) => setTemplateName(e.target.value)} /></label>
                    <label>Product for value preview (optional)<select value={productId} onChange={(e) => setProductId(e.target.value)}><option value="">Save template without preview</option>{products.map(product => <option key={product.product_id} value={product.product_id}>{product.product_id} - {product.model || product.manufacturer || product.product_type}</option>)}</select></label>
                    <div className="form-grid">
                        <label>Stakeholder role<select value={role} onChange={(e) => setRole(e.target.value)}><option value="">Any role</option>{roles.map(r => <option key={r.name} value={r.name}>{r.display_name}</option>)}</select></label>
                        <label>Lifecycle event<select value={event} onChange={(e) => setEvent(e.target.value)}><option value="">Any event</option>{events.map(ev => <option key={ev.name} value={ev.name}>{ev.display_name}</option>)}</select></label>
                    </div>
                    <div className="form-grid">
                        <label>Custom event name (optional)<input value={customEvent} maxLength={100} onChange={(e) => setCustomEvent(e.target.value)} placeholder="e.g. Inverter inspection" /></label>
                        <label>Lifecycle phase
                            <select value={effectivePhase} disabled={Boolean(event)} onChange={(e) => setLifecyclePhase(e.target.value)}>
                                <option value="">Any phase</option>
                                {lifecyclePhases.map(phase => <option key={phase.name} value={phase.name}>{phase.display_name}</option>)}
                            </select>
                        </label>
                    </div>
                    <p className="filter-help">Define your own decision context by naming the event and assigning it to a lifecycle phase. A template without a predefined event counts as a dynamic signal for every event of its phase; with a predefined event, the phase follows from that event.</p>
                    <div className="selected-term-panel">
                        <div className="selected-term-header"><h3>Selected terms</h3><span>{selectedTerms.length}</span></div>
                        {selectedTerms.length > 0 ? <div className="chip-list">{selectedTerms.map(term => <button key={term} type="button" className="selected-term-chip" onClick={() => toggleTerm(term)}>{termMetadata[term]?.display_name || term}</button>)}</div> : <p className="muted-text">No terms selected yet.</p>}
                    </div>
                    <div className="builder-actions">
                        <button className="primary-action" type="submit" disabled={localLoading}><ListChecks /> {editingTemplateId ? 'Update template' : 'Save template'}</button>
                        {editingTemplateId && <button className="secondary-action" type="button" onClick={resetTemplateForm}>Cancel edit</button>}
                    </div>
                </div>
                <div className="term-picker">
                    <div className="term-picker-toolbar">
                        <input value={termFilter} onChange={(e) => setTermFilter(e.target.value)} placeholder="Search vocabulary terms..." />
                        <button type="button" className="secondary-action" onClick={selectPromoted} disabled={promotedTerms.length === 0}>Use dynamic recommendations</button>
                    </div>
                    <div className="term-category-list">
                        {Object.entries(termsByCategory).map(([category, categoryTerms]) => (
                            <div key={category} className="term-category">
                                <h3>{CATEGORY_DISPLAY[category] || prettifyKey(category)}</h3>
                                <div className="term-grid">
                                    {categoryTerms.map(term => {
                                        const selected = selectedTerms.includes(term.field_name);
                                        const promoted = promotedTerms.some(t => t.field_name === term.field_name);
                                        return <button key={term.field_name} type="button" className={`term-option ${selected ? 'selected' : ''}`} onClick={() => toggleTerm(term.field_name)}>{selected ? <CheckSquare /> : <Square />}<span><strong>{term.display_name}</strong><small>{term.description}</small>{promoted && <em>Dynamic recommendation</em>}</span></button>;
                                    })}
                                </div>
                            </div>
                        ))}
                    </div>
                </div>
            </form>
            {result && resultFields.length > 0 && (
                <section className="builder-result">
                    <div className="builder-result-header"><h3>{result.template_name}</h3><p>{result.product_id} - {result.product_type}{result.custom_event ? ` · ${result.custom_event}` : ''}{result.lifecycle_phase ? ` · ${phaseLabel(result.lifecycle_phase)}` : ''}</p></div>
                    <div className="categories-grid">
                        {resultFields.map(field => <div key={field.field_name} className="field-row custom-field-row"><span className={`field-priority ${field.available ? 'high' : 'low'}`}>{field.available ? 'OK' : 'NA'}</span><div className="field-info"><div className="field-name-row"><div className="field-name">{field.display_name}</div><span className="priority-label">{field.available ? 'Value found' : 'No value found'}</span></div>{field.sources?.length > 0 && <div className="field-sources">{field.sources.map(source => <span key={source} className="source-badge"><Server /> {source}</span>)}</div>}<div className="field-value">{renderFieldValue(field)}</div></div></div>)}
                    </div>
                </section>
            )}
            <section className="template-history">
                <h3>Stored dynamic templates</h3>
                {templates.length > 0 ? (
                    <div className="template-list">
                        {templates.map(template => (
                            <div key={template.template_id} className={`template-item ${editingTemplateId === template.template_id ? 'editing' : ''}`}>
                                <strong>{template.template_name}</strong>
                                <span>{template.terms?.length || 0} terms</span>
                                <span className="template-context">
                                    {[
                                        template.role ? roleLabel(template.role) : 'Any role',
                                        template.custom_event || (template.event ? eventLabel(template.event) : 'Any event'),
                                        template.lifecycle_phase ? phaseLabel(template.lifecycle_phase) : null,
                                        template.product_type ? prettifyKey(template.product_type) : null,
                                    ].filter(Boolean).join(' · ')}
                                </span>
                                <div className="template-term-preview">
                                    {(template.terms || []).slice(0, 5).map(term => <small key={term}>{termMetadata[term]?.display_name || term}</small>)}
                                </div>
                                <div className="template-actions">
                                    <button type="button" className="secondary-action" onClick={() => editTemplate(template)}>Edit</button>
                                    <button type="button" className="icon-danger-btn" onClick={() => deleteTemplate(template.template_id)} disabled={localLoading} title="Delete template"><Trash2 /></button>
                                </div>
                            </div>
                        ))}
                    </div>
                ) : (
                    <p className="muted-text">No custom templates stored yet.</p>
                )}
            </section>
        </div>
    );
}

function SssomMappingsView({ mappingSets, mappings, onRefresh }) {
    const [query, setQuery] = useState('');
    const [prefix, setPrefix] = useState('all');

    const prefixes = Array.from(new Set(
        mappings
            .flatMap(mapping => [mapping.subject_id, mapping.object_id])
            .map(curie => String(curie || '').split(':')[0])
            .filter(Boolean)
    )).sort();

    const filteredMappings = mappings.filter(mapping => {
        const haystack = [
            mapping.subject_id,
            mapping.subject_label,
            mapping.predicate_id,
            mapping.object_id,
            mapping.object_label,
            mapping.mapping_justification,
            mapping.mapping_tool,
            ...(mapping.local_terms || []).flatMap(term => [term.name, term.label, term.type]),
        ].join(' ').toLowerCase();
        const matchesQuery = haystack.includes(query.toLowerCase());
        const matchesPrefix = prefix === 'all'
            || String(mapping.subject_id || '').startsWith(`${prefix}:`)
            || String(mapping.object_id || '').startsWith(`${prefix}:`);
        return matchesQuery && matchesPrefix;
    });

    const linkedLocalCount = mappings.filter(mapping => (mapping.local_terms || []).length > 0).length;
    const averageConfidence = mappings.length
        ? Math.round((mappings.reduce((sum, mapping) => sum + Number(mapping.confidence || 0), 0) / mappings.length) * 100)
        : 0;
    const mappingSet = mappingSets[0] || {};
    const curieMap = mappingSet.curie_map || {};

    return (
        <div className="sssom-view">
            <div className="builder-header">
                <div>
                    <h2>SSSOM mappings</h2>
                    <p>Ontology mappings from the Digital Product Memory vocabulary to external terms. Linked local terms show which project concepts are represented by each SSSOM subject.</p>
                </div>
                <button className="back-btn" onClick={onRefresh} style={{ marginBottom: 0 }}><RefreshCw /> Refresh</button>
            </div>

            <div className="passport-stats">
                <div className="stat-card"><div className="stat-value">{mappings.length}</div><div className="stat-label">Mappings</div></div>
                <div className="stat-card"><div className="stat-value">{linkedLocalCount}</div><div className="stat-label">Linked local terms</div></div>
                <div className="stat-card"><div className="stat-value">{prefixes.length}</div><div className="stat-label">CURIE prefixes</div></div>
                <div className="stat-card"><div className="stat-value">{averageConfidence}%</div><div className="stat-label">Avg confidence</div></div>
            </div>

            <section className="sssom-summary">
                <div>
                    <h3>{mappingSet.mapping_set_id || 'Mapping set'}</h3>
                    <p>Version {mappingSet.mapping_set_version || 'n/a'}{mappingSet.license && ` - ${mappingSet.license}`}</p>
                </div>
                {Object.keys(curieMap).length > 0 && (
                    <div className="sssom-prefix-list">
                        {Object.entries(curieMap).map(([key, value]) => <span key={key} title={value}>{key}</span>)}
                    </div>
                )}
            </section>

            <section className="sssom-toolbar">
                <div className="search-input-wrapper">
                    <Search />
                    <input
                        className="search-input"
                        value={query}
                        onChange={(e) => setQuery(e.target.value)}
                        placeholder="Search mapped terms, IDs, predicates..."
                    />
                </div>
                <select className="filter-select" value={prefix} onChange={(e) => setPrefix(e.target.value)}>
                    <option value="all">All prefixes</option>
                    {prefixes.map(item => <option key={item} value={item}>{item}</option>)}
                </select>
            </section>

            {filteredMappings.length > 0 ? (
                <div className="sssom-list">
                    {filteredMappings.map(mapping => {
                        const matchInfo = getSkosMatchInfo(mapping.predicate_id);
                        return (
                            <div key={mapping.mapping_id} className="sssom-item">
                                <div className="sssom-map-line">
                                    <div className="sssom-term">
                                        <strong>{mapping.subject_label || mapping.subject_id}</strong>
                                        <code>{mapping.subject_id}</code>
                                    </div>
                                    <div
                                        className="sssom-predicate"
                                        title={`${matchInfo.label}: ${matchInfo.description}`}
                                        aria-label={`${mapping.predicate_id} - ${matchInfo.description}`}
                                    >
                                        <Waypoints />
                                        <span>{mapping.predicate_id}</span>
                                        <small>{matchInfo.label}</small>
                                    </div>
                                    <div className="sssom-term">
                                        <strong>{mapping.object_label || mapping.object_id}</strong>
                                        <code>{mapping.object_id}</code>
                                    </div>
                                </div>
                                <p className="sssom-match-description">{matchInfo.description}</p>
                                <div className="sssom-meta-row">
                                    <span className={`data-badge ${Number(mapping.confidence || 0) >= 0.85 ? 'green' : 'blue'}`}>
                                        {Math.round(Number(mapping.confidence || 0) * 100)}% confidence
                                    </span>
                                    {mapping.mapping_justification && <span className="data-chip">{mapping.mapping_justification}</span>}
                                    {mapping.mapping_tool && <span className="data-chip">{mapping.mapping_tool}</span>}
                                </div>
                                {(mapping.local_terms || []).length > 0 && (
                                    <div className="sssom-local-terms">
                                        <span>Local Digital Product Memory terms</span>
                                        <div className="chip-list">
                                            {mapping.local_terms.map(term => (
                                                <span key={`${mapping.mapping_id}-${term.type}-${term.name}`} className="selected-term-chip">
                                                    {term.label || term.name} <small>{term.type}</small>
                                                </span>
                                            ))}
                                        </div>
                                    </div>
                                )}
                            </div>
                        );
                    })}
                </div>
            ) : (
                <div className="empty-state">
                    <Waypoints />
                    <h3>No SSSOM mappings found</h3>
                    <p>Try another search or refresh after the recommendation engine has seeded Neo4j.</p>
                </div>
            )}
        </div>
    );
}

function RegistryView({ services, onRefresh }) {
    const [discoverUrl, setDiscoverUrl] = useState('');
    const [form, setForm] = useState({
        name: '',
        provider: '',
        description: '',
        base_url: '',
        product_types: '',
        data_categories: '',
    });
    const [submitting, setSubmitting] = useState(false);
    const [message, setMessage] = useState(null);

    function csvToList(value) {
        return value.split(',').map(v => v.trim()).filter(Boolean);
    }

    function updateForm(key, value) {
        setForm(prev => ({ ...prev, [key]: value }));
    }

    async function handleManualRegister(e) {
        e.preventDefault();
        setSubmitting(true);
        setMessage(null);
        try {
            await api.registerService({
                name: form.name,
                provider: form.provider,
                description: form.description,
                base_url: form.base_url,
                product_types: csvToList(form.product_types),
                data_categories: csvToList(form.data_categories),
                conditions: { requires_auth: false },
            });
            setForm({ name: '', provider: '', description: '', base_url: '', product_types: '', data_categories: '' });
            setMessage({ type: 'success', text: 'Service registered successfully.' });
            await onRefresh();
        } catch (e) {
            setMessage({ type: 'error', text: e.message });
        } finally {
            setSubmitting(false);
        }
    }

    async function handleDiscover(e) {
        e.preventDefault();
        setSubmitting(true);
        setMessage(null);
        try {
            const result = await api.discoverService(discoverUrl, true);
            const warnings = result.warnings?.length ? ` Warnings: ${result.warnings.join(' ')}` : '';
            setDiscoverUrl('');
            setMessage({ type: 'success', text: `Discovered from ${result.discovered_from} and registered "${result.endpoint.name}".${warnings}` });
            await onRefresh();
        } catch (e) {
            setMessage({ type: 'error', text: e.message });
        } finally {
            setSubmitting(false);
        }
    }

    async function handleDelete(serviceId) {
        setSubmitting(true);
        setMessage(null);
        try {
            await api.deleteService(serviceId);
            setMessage({ type: 'success', text: 'Service removed.' });
            await onRefresh();
        } catch (e) {
            setMessage({ type: 'error', text: e.message });
        } finally {
            setSubmitting(false);
        }
    }

    return (
        <div>
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 20 }}>
                <div>
                    <h2 style={{ fontSize: 22, fontWeight: 700, letterSpacing: '-0.02em' }}>Service Registry</h2>
                    <p style={{ fontSize: 14, color: '#6e6e73', marginTop: 4 }}>
                        Registered data provider endpoints
                    </p>
                </div>
                <button className="back-btn" onClick={onRefresh} style={{ marginBottom: 0 }}>
                    <RefreshCw /> Refresh
                </button>
            </div>

            <section className="registry-guide">
                <div>
                    <h3>Connect a data provider</h3>
                    <p>
                        A provider becomes usable when it exposes product data and is listed in the registry.
                        The Resolver calls registered providers at <code>/products/&lbrace;product_id&rbrace;</code>,
                        merges their responses, and sends the combined passport to the Knowledge Graph.
                    </p>
                </div>
                <div className="registry-guide-steps">
                    <span>1. Run provider</span>
                    <span>2. Register URL</span>
                    <span>3. Resolve product</span>
                </div>
            </section>

            {message && (
                <div className={`registry-message ${message.type}`}>
                    {message.type === 'error' ? <AlertTriangle /> : <Info />}
                    <span>{message.text}</span>
                </div>
            )}

            <div className="registry-actions-grid">
                <form className="registry-form" onSubmit={handleDiscover}>
                    <div className="registry-form-header">
                        <Wand2 />
                        <div>
                            <h3>Auto-discover service</h3>
                            <p>Enter the provider base URL, not the Swagger docs URL. In Docker Compose use the service name, for example http://midlife-purchase-provider:8022.</p>
                        </div>
                    </div>
                    <label>
                        Base URL
                        <input
                            type="url"
                            value={discoverUrl}
                            placeholder="http://midlife-purchase-provider:8022"
                            onChange={(e) => setDiscoverUrl(e.target.value)}
                            required
                        />
                    </label>
                    <button className="primary-action" type="submit" disabled={submitting}>
                        <Wand2 /> Discover and register
                    </button>
                </form>

                <form className="registry-form" onSubmit={handleManualRegister}>
                    <div className="registry-form-header">
                        <Plus />
                        <div>
                            <h3>Manual registration</h3>
                            <p>Use this when the provider has no metadata endpoint yet.</p>
                        </div>
                    </div>
                    <div className="form-grid">
                        <label>
                            Name
                            <input value={form.name} onChange={(e) => updateForm('name', e.target.value)} placeholder="Repair Data Provider" required />
                        </label>
                        <label>
                            Base URL
                            <input type="url" value={form.base_url} onChange={(e) => updateForm('base_url', e.target.value)} placeholder="http://repair-provider:8020" required />
                        </label>
                        <label>
                            Provider
                            <input value={form.provider} onChange={(e) => updateForm('provider', e.target.value)} placeholder="Example Company" />
                        </label>
                        <label>
                            Product types
                            <input value={form.product_types} onChange={(e) => updateForm('product_types', e.target.value)} placeholder="washing_machine, lithium_battery" />
                        </label>
                    </div>
                    <label>
                        Data categories
                        <input value={form.data_categories} onChange={(e) => updateForm('data_categories', e.target.value)} placeholder="materials, components, maintenance" />
                    </label>
                    <label>
                        Description
                        <textarea value={form.description} onChange={(e) => updateForm('description', e.target.value)} placeholder="Short description of the data this provider contributes." />
                    </label>
                    <button className="primary-action" type="submit" disabled={submitting}>
                        <Plus /> Register service
                    </button>
                </form>
            </div>

            {services.length > 0 ? (
                <div className="registry-list">
                    {services.map(s => (
                        <div key={s.id} className="registry-item">
                            <div className="registry-item-header">
                                <h3>{s.name}</h3>
                                <div className="registry-item-actions">
                                    <span className={`status-dot ${s.status || 'active'}`} />
                                    <button
                                        className="icon-danger-btn"
                                        type="button"
                                        onClick={() => handleDelete(s.id)}
                                        disabled={submitting}
                                        title="Remove service"
                                    >
                                        <Trash2 />
                                    </button>
                                </div>
                            </div>
                            {s.provider && <div className="provider">{s.provider}</div>}
                            <div className="url">{s.base_url}</div>
                            {s.description && <p style={{ fontSize: 13, color: '#6e6e73', marginBottom: 8 }}>{s.description}</p>}
                            <div className="tag-list">
                                {(s.product_types || []).map(t => (
                                    <span key={t} className="tag">{PRODUCT_TYPE_LABELS[t] || t}</span>
                                ))}
                                {(s.data_categories || []).map(c => (
                                    <span key={c} className="tag">{c}</span>
                                ))}
                            </div>
                        </div>
                    ))}
                </div>
            ) : (
                <div className="empty-state">
                    <Server />
                    <h3>No services registered</h3>
                    <p>Register a data provider to get started.</p>
                </div>
            )}
        </div>
    );
}
