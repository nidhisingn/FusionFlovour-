import React, { useCallback, useEffect, useMemo, useState } from 'react';
import {
  Alert,
  Box,
  Button,
  Card,
  CardContent,
  Chip,
  CircularProgress,
  Container,
  Dialog,
  DialogActions,
  DialogContent,
  DialogTitle,
  Divider,
  LinearProgress,
  List,
  ListItem,
  ListItemText,
  Paper,
  Stack,
  TextField,
  Typography,
} from '@mui/material';
import AddIcon from '@mui/icons-material/Add';
import ArticleIcon from '@mui/icons-material/Article';
import AutoAwesomeIcon from '@mui/icons-material/AutoAwesome';
import CloseIcon from '@mui/icons-material/Close';
import HistoryIcon from '@mui/icons-material/History';
import HomeOutlinedIcon from '@mui/icons-material/HomeOutlined';
import InfoIcon from '@mui/icons-material/Info';
import LoginIcon from '@mui/icons-material/Login';
import MenuBookOutlinedIcon from '@mui/icons-material/MenuBookOutlined';
import PersonAddAlt1Icon from '@mui/icons-material/PersonAddAlt1';
import PsychologyAltOutlinedIcon from '@mui/icons-material/PsychologyAltOutlined';
import RestaurantIcon from '@mui/icons-material/Restaurant';
import SecurityOutlinedIcon from '@mui/icons-material/SecurityOutlined';
import SpeedOutlinedIcon from '@mui/icons-material/SpeedOutlined';
import './App.css';

type ViewKey = 'home' | 'login' | 'signup' | 'articles' | 'history';

function App() {
  const API_BASE = 'http://localhost:8080';
  const [allergyInsights, setAllergyInsights] = useState<any[]>([]);
  const [ingredientInput, setIngredientInput] = useState('');
  const [ingredients, setIngredients] = useState<string[]>([]);
  const [prediction, setPrediction] = useState('');
  const [alternatives, setAlternatives] = useState<Array<[string, number]>>([]);
  const [substitutions, setSubstitutions] = useState<any[]>([]);
  const [normalizationMap, setNormalizationMap] = useState<any[]>([]);
  const [dietMatch, setDietMatch] = useState<any>(null);
  const [cuisineTags, setCuisineTags] = useState<string[]>([]);
  const [personalizationHint, setPersonalizationHint] = useState('');
  const [explanation, setExplanation] = useState('');
  const [relatedArticles, setRelatedArticles] = useState<any[]>([]);
  const [articles, setArticles] = useState<any[]>([]);
  const [history, setHistory] = useState<any[]>([]);
  const [currentView, setCurrentView] = useState<ViewKey>('home');
  const [confidence, setConfidence] = useState<number | null>(null);
  const [stepsOpen, setStepsOpen] = useState(false);
  const [stepsTitle, setStepsTitle] = useState('');
  const [stepsLoading, setStepsLoading] = useState(false);
  const [stepsError, setStepsError] = useState('');
  const [steps, setSteps] = useState<string[]>([]);
  const [sourceUrl, setSourceUrl] = useState<string>('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [authName, setAuthName] = useState('');
  const [authEmail, setAuthEmail] = useState('');
  const [authPassword, setAuthPassword] = useState('');
  const [authError, setAuthError] = useState('');
  const [authLoading, setAuthLoading] = useState(false);
  const [token, setToken] = useState<string>(() => localStorage.getItem('recipe_token') || '');
  const [user, setUser] = useState<any>(() => {
    const raw = localStorage.getItem('recipe_user');
    return raw ? JSON.parse(raw) : null;
  });
  const [articleRecipeTitle, setArticleRecipeTitle] = useState('');
  const [articleTitle, setArticleTitle] = useState('');
  const [articleSummary, setArticleSummary] = useState('');
  const [articleContent, setArticleContent] = useState('');
  const [articleTags, setArticleTags] = useState('');
  const [articleImage, setArticleImage] = useState<File | null>(null);
  const [articleStatus, setArticleStatus] = useState('');
  const [articleError, setArticleError] = useState('');
  const [allergyProfileInput, setAllergyProfileInput] = useState('');
  const [preferredCuisineInput, setPreferredCuisineInput] = useState('');
  const [dietPreferenceInput, setDietPreferenceInput] = useState('balanced');
  const [preferenceStatus, setPreferenceStatus] = useState('');

  const authHeaders = useMemo<HeadersInit>(() => {
    const headers: Record<string, string> = {};
    if (token) {
      headers.Authorization = `Bearer ${token}`;
    }
    return headers;
  }, [token]);

  const fetchArticles = useCallback(async () => {
    try {
      const res = await fetch(`${API_BASE}/articles`);
      const data = await res.json();
      if (Array.isArray(data)) setArticles(data);
    } catch {}
  }, [API_BASE]);

  const handleLogout = useCallback(() => {
    setToken('');
    setUser(null);
    localStorage.removeItem('recipe_token');
    localStorage.removeItem('recipe_user');
  }, []);

  const fetchMe = useCallback(async () => {
    try {
      const res = await fetch(`${API_BASE}/auth/me`, { headers: authHeaders });
      if (!res.ok) {
        handleLogout();
        return;
      }
      const data = await res.json();
      setUser(data);
      localStorage.setItem('recipe_user', JSON.stringify(data));
    } catch {
      handleLogout();
    }
  }, [API_BASE, authHeaders, handleLogout]);

  const fetchHistory = useCallback(async () => {
    try {
      const res = await fetch(`${API_BASE}/history`, { headers: authHeaders });
      const data = await res.json();
      if (res.ok && Array.isArray(data)) setHistory(data);
    } catch {}
  }, [API_BASE, authHeaders]);

  useEffect(() => {
    if (user) {
      setAllergyProfileInput((user.allergyProfile || []).join(', '));
      setPreferredCuisineInput((user.preferredCuisines || []).join(', '));
      setDietPreferenceInput(user.dietPreference || 'balanced');
    }
  }, [user]);

  useEffect(() => {
    fetchArticles();
  }, [fetchArticles]);

  useEffect(() => {
    if (token) {
      fetchMe();
      fetchHistory();
    } else {
      setHistory([]);
    }
  }, [token, fetchMe, fetchHistory]);

  const fetchCookingSteps = async (title: string) => {
    setStepsOpen(true);
    setStepsTitle(title);
    setStepsLoading(true);
    setStepsError('');
    setSteps([]);
    setSourceUrl('');
    try {
      const res = await fetch(`${API_BASE}/recipe-info?title=${encodeURIComponent(title)}`);
      const data = await res.json();
      if (!res.ok) {
        setStepsError(data.error || 'Failed to fetch cooking steps');
        return;
      }
      if (Array.isArray(data.steps)) setSteps(data.steps);
      if (typeof data.sourceUrl === 'string') setSourceUrl(data.sourceUrl);
    } catch (e: any) {
      setStepsError(e.message || 'Failed to fetch cooking steps');
    } finally {
      setStepsLoading(false);
    }
  };

  const handleAddIngredient = () => {
    const newIng = ingredientInput.trim().toLowerCase();
    if (newIng && !ingredients.includes(newIng)) {
      setIngredients((prev) => [...prev, newIng]);
      setIngredientInput('');
    }
  };

  const handleInputKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' || e.key === ',' || e.key === ';') {
      e.preventDefault();
      handleAddIngredient();
    }
  };

  const handleDelete = (ing: string) => {
    setIngredients((prev) => prev.filter((item) => item !== ing));
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setPrediction('');
    setAlternatives([]);
    setRelatedArticles([]);
    setAllergyInsights([]);
    setSubstitutions([]);
    setNormalizationMap([]);
    setDietMatch(null);
    setCuisineTags([]);
    setPersonalizationHint('');
    setExplanation('');
    setConfidence(null);
    setError('');
    try {
      const response = await fetch(`${API_BASE}/predict`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', ...(authHeaders as Record<string, string>) },
        body: JSON.stringify({ ingredients: ingredients.join(',') }),
      });
      const data = await response.json();
      if (response.ok && data.prediction) {
        setPrediction(data.prediction);
        if (Array.isArray(data.alternatives)) setAlternatives(data.alternatives);
        if (typeof data.confidence === 'number') setConfidence(data.confidence);
        if (Array.isArray(data.relatedArticles)) setRelatedArticles(data.relatedArticles);
        if (Array.isArray(data.allergyInsights)) setAllergyInsights(data.allergyInsights);
        if (Array.isArray(data.substitutions)) setSubstitutions(data.substitutions);
        if (Array.isArray(data.normalizationMap)) setNormalizationMap(data.normalizationMap);
        if (data.dietMatch) setDietMatch(data.dietMatch);
        if (Array.isArray(data.cuisineTags)) setCuisineTags(data.cuisineTags);
        if (typeof data.personalizationHint === 'string') setPersonalizationHint(data.personalizationHint);
        if (typeof data.explanation === 'string') setExplanation(data.explanation);
        if (data.userPreferences) {
          setUser((prev: any) => ({ ...(prev || {}), ...data.userPreferences }));
        }
        if (token) fetchHistory();
      } else {
        setError(data.error || 'Error from backend');
      }
    } catch (e: any) {
      setError(e.message || 'Unknown error');
    } finally {
      setLoading(false);
    }
  };

  const handlePreferenceSave = async () => {
    if (!token) {
      setPreferenceStatus('Login required to save preferences.');
      return;
    }
    setPreferenceStatus('');
    try {
      const res = await fetch(`${API_BASE}/auth/preferences`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json', ...(authHeaders as Record<string, string>) },
        body: JSON.stringify({
          allergyProfile: allergyProfileInput.split(',').map((v) => v.trim()).filter(Boolean),
          preferredCuisines: preferredCuisineInput.split(',').map((v) => v.trim()).filter(Boolean),
          dietPreference: dietPreferenceInput,
        }),
      });
      const data = await res.json();
      if (!res.ok) {
          setPreferenceStatus(data.error || 'Failed to save preferences');
        return;
      }
      setUser(data.user);
      localStorage.setItem('recipe_user', JSON.stringify(data.user));
      setPreferenceStatus('Preferences saved successfully.');
    } catch (e: any) {
      setPreferenceStatus(e.message || 'Failed to save preferences');
    }
  };

  const submitAuth = async (mode: 'login' | 'signup', e: React.FormEvent) => {
    e.preventDefault();
    setAuthLoading(true);
    setAuthError('');
    try {
      const payload: any = { email: authEmail, password: authPassword };
      if (mode === 'signup') payload.name = authName;
      const res = await fetch(`${API_BASE}/auth/${mode}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      });
      const data = await res.json();
      if (!res.ok) {
        setAuthError(data.error || 'Authentication failed');
        return;
      }
      setToken(data.token);
      setUser(data.user);
      localStorage.setItem('recipe_token', data.token);
      localStorage.setItem('recipe_user', JSON.stringify(data.user));
      setAuthName('');
      setAuthEmail('');
      setAuthPassword('');
      setCurrentView('home');
    } catch (e: any) {
      setAuthError(e.message || 'Authentication failed');
    } finally {
      setAuthLoading(false);
    }
  };

  const handleArticleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setArticleError('');
    setArticleStatus('');
    if (!token) {
      setArticleError('Please login first');
      return;
    }
    try {
      const form = new FormData();
      form.append('recipeTitle', articleRecipeTitle);
      form.append('title', articleTitle);
      form.append('summary', articleSummary);
      form.append('content', articleContent);
      form.append('tags', articleTags);
      if (articleImage) form.append('image', articleImage);
      const res = await fetch(`${API_BASE}/articles`, {
        method: 'POST',
        headers: authHeaders,
        body: form,
      });
      const data = await res.json();
      if (!res.ok) {
        setArticleError(data.error || 'Failed to create article');
        return;
      }
      setArticleStatus('Article created successfully');
      setArticleRecipeTitle('');
      setArticleTitle('');
      setArticleSummary('');
      setArticleContent('');
      setArticleTags('');
      setArticleImage(null);
      fetchArticles();
    } catch (e: any) {
      setArticleError(e.message || 'Failed to create article');
    }
  };

  const fullImageUrl = (imageUrl?: string) => (imageUrl ? `${API_BASE}${imageUrl}` : '');

  const normalizeScore = useCallback((score: number, maxScore: number) => {
    if (!Number.isFinite(score) || !Number.isFinite(maxScore) || maxScore <= 0) {
      return 0;
    }
    return Math.max(0, Math.min(100, (score / maxScore) * 100));
  }, []);

  const topAlternativeScore = useMemo(() => {
    if (!alternatives.length) return 0;
    return Math.max(...alternatives.map(([, score]) => Number(score) || 0));
  }, [alternatives]);

  const displayConfidence = useMemo(() => {
    if (typeof confidence !== 'number') return null;
    return normalizeScore(confidence, topAlternativeScore || confidence);
  }, [confidence, normalizeScore, topAlternativeScore]);

  const navItems = [
    { key: 'home' as ViewKey, label: 'Home', icon: <HomeOutlinedIcon /> },
    { key: 'login' as ViewKey, label: 'Login', icon: <LoginIcon /> },
    { key: 'signup' as ViewKey, label: 'Signup', icon: <PersonAddAlt1Icon /> },
    { key: 'articles' as ViewKey, label: 'Articles', icon: <ArticleIcon /> },
    { key: 'history' as ViewKey, label: 'History', icon: <HistoryIcon /> },
  ];

  const infoCards = [
    {
      title: 'Recipe prediction',
      text: 'Enter ingredients and instantly get the most likely recipe along with confidence and alternatives.',
      icon: <RestaurantIcon />,
    },
    {
      title: 'Food articles',
      text: 'Create and read useful recipe articles with summaries, tags, and uploaded images.',
      icon: <MenuBookOutlinedIcon />,
    },
    {
      title: 'Saved history',
      text: 'Login to keep track of your previous predictions and revisit useful ingredient combinations.',
      icon: <HistoryIcon />,
    },
  ];

  const featureHighlights = [
    {
      title: 'Smart recipe outlet',
      text: 'A focused prediction panel with ingredient entry, clear call-to-action, and instant result feedback.',
      icon: <PsychologyAltOutlinedIcon />,
    },
    {
      title: 'Allergy-aware guidance',
      text: 'Get practical warnings and safer recommendations when ingredients or predicted dishes suggest allergy risks.',
      icon: <SecurityOutlinedIcon />,
    },
    {
      title: 'Fast AI workflow',
      text: 'View alternatives, cooking steps, related articles, and prediction history in one polished experience.',
      icon: <SpeedOutlinedIcon />,
    },
  ];

  const quickStats = [
    { label: 'Ingredients added', value: ingredients.length.toString().padStart(2, '0') },
    { label: 'Articles available', value: String(articles.length) },
    { label: 'History saved', value: user ? String(history.length) : 'Login' },
  ];

  const renderPredictionResults = () => (
    <>
      {(loading || error || prediction) && (
        <Paper className="section-card results-card" elevation={0}>
          <Box className="results-header-row">
            <Box>
              <Typography className="page-kicker">Prediction workspace</Typography>
              <Typography className="section-title">Results & recommendations</Typography>
              <Typography className="section-subtitle">
                Your recipe match, alternatives, safety alerts, and article references appear here.
              </Typography>
            </Box>
            {prediction && (
              <Chip
                icon={<AutoAwesomeIcon />}
                label={`Best match: ${prediction}`}
                className="result-summary-chip"
              />
            )}
          </Box>

          {loading && (
            <Box className="loading-panel">
              <CircularProgress size={28} />
              <Box sx={{ flex: 1 }}>
                <Typography sx={{ fontWeight: 700 }}>Analyzing your ingredients…</Typography>
                <LinearProgress sx={{ mt: 1.2, borderRadius: 999 }} />
              </Box>
            </Box>
          )}

          {error && <Alert severity="error" sx={{ mt: 2 }}>{error}</Alert>}

          {prediction && !loading && (
            <>
              <Box className="results-grid">
                <Paper className="result-highlight-card" elevation={0}>
                  <Typography className="page-kicker">Top result</Typography>
                  <Typography className="result-title-main">{prediction}</Typography>
                  <Typography className="muted-text" sx={{ mt: 1 }}>
                    This recipe best matches your selected ingredient pattern.
                  </Typography>
                  {typeof displayConfidence === 'number' && (
                    <Box sx={{ mt: 2.2 }}>
                      <Box className="progress-label-row">
                        <Typography variant="body2">Confidence</Typography>
                        <Typography variant="body2" sx={{ fontWeight: 700 }}>
                          {displayConfidence.toFixed(0)}%
                        </Typography>
                      </Box>
                      <LinearProgress
                        variant="determinate"
                        value={displayConfidence}
                        className="confidence-bar"
                      />
                    </Box>
                  )}
                </Paper>

                <Paper className="result-insight-card" elevation={0}>
                  <Typography className="mini-title">Selected ingredients</Typography>
                  <Typography className="muted-text" sx={{ mt: 1 }}>
                    {ingredients.length
                      ? ingredients.join(', ')
                      : 'No ingredients were included for this prediction.'}
                  </Typography>
                </Paper>
              </Box>

              {alternatives.length > 0 && (
                <Box className="result-block">
                  <Typography className="mini-title">Recommended options</Typography>
                  <Box className="alternatives-stack">
                    {alternatives.map(([name, score], idx) => {
                      const normalizedScore = normalizeScore(Number(score), topAlternativeScore);
                      return (
                        <Paper key={`${name}-${idx}`} className="alternative-card" elevation={0}>
                          <Box>
                            <Typography sx={{ fontWeight: 700 }}>{idx + 1}. {name}</Typography>
                            <Typography variant="body2" className="muted-text">
                              Match score: {normalizedScore.toFixed(0)}%
                            </Typography>
                          </Box>
                          <Button
                            size="small"
                            variant="outlined"
                            startIcon={<InfoIcon />}
                            onClick={() => fetchCookingSteps(name)}
                          >
                            Steps
                          </Button>
                        </Paper>
                      );
                    })}
                  </Box>
                </Box>
              )}

              {(personalizationHint || explanation || cuisineTags.length > 0 || dietMatch || normalizationMap.length > 0 || substitutions.length > 0) && (
                <Box className="result-block result-support-block">
                  <Stack spacing={1.2} sx={{ mt: 1.5 }}>
                    {dietMatch && (
                      <Alert severity={dietMatch.compatible ? 'success' : 'warning'}>
                        Diet preference: {dietMatch.diet}. {dietMatch.compatible ? 'Looks compatible with selected ingredients.' : `Potential conflicts: ${(dietMatch.conflicts || []).join(', ')}`}
                      </Alert>
                    )}
                    {normalizationMap.length > 0 && (
                      <Box>
                        <Typography variant="body2" sx={{ fontWeight: 700, mb: 1 }}>Normalized ingredients</Typography>
                        <Stack spacing={0.8}>
                          {normalizationMap.map((row, idx) => (
                            <Typography key={`${row.input}-${idx}`} variant="body2" className="muted-text">
                              {row.input} → {row.normalized}
                            </Typography>
                          ))}
                        </Stack>
                      </Box>
                    )}
                    {substitutions.length > 0 && (
                      <Box>
                        <Typography variant="body2" sx={{ fontWeight: 700, mb: 1 }}>Ingredient substitutions</Typography>
                        <Stack spacing={1}>
                          {substitutions.map((row, idx) => (
                            <Paper key={`${row.ingredient}-${idx}`} className="alternative-card" elevation={0}>
                              <Box>
                                <Typography sx={{ fontWeight: 700 }}>{row.ingredient}</Typography>
                                <Typography variant="body2" className="muted-text">{row.alternatives?.join(', ')}</Typography>
                                <Typography variant="body2" className="muted-text">{row.reason}</Typography>
                              </Box>
                            </Paper>
                          ))}
                        </Stack>
                      </Box>
                    )}
                  </Stack>
                </Box>
              )}

              {allergyInsights.length > 0 && (
                <Box className="result-block">
                  <Typography className="mini-title">Allergy-aware recommendations</Typography>
                  <Stack spacing={1.5} sx={{ mt: 1.5 }}>
                    {allergyInsights.map((insight, idx) => {
                      const severity = insight.severity === 'high' ? 'warning' : insight.severity === 'medium' ? 'info' : 'success';
                      return (
                        <Alert key={`${insight.allergen}-${idx}`} severity={severity as any} className="allergy-alert-card">
                          <Box className="allergy-alert-header">
                            <Typography sx={{ fontWeight: 800, textTransform: 'capitalize' }}>
                              {insight.allergen} check
                            </Typography>
                            <Chip
                              label={`${insight.severity || 'low'} risk`}
                              size="small"
                              className={`allergy-chip ${insight.severity || 'low'}`}
                            />
                          </Box>
                          <Typography variant="body2" sx={{ mt: 0.8 }}>{insight.message}</Typography>
                          <Typography variant="body2" sx={{ mt: 0.8, fontWeight: 700 }}>
                            {insight.recommendation}
                          </Typography>
                          {!!insight.matchedIngredients?.length && (
                            <Stack direction="row" spacing={1} sx={{ mt: 1.2, flexWrap: 'wrap' }}>
                              {insight.matchedIngredients.map((item: string) => (
                                <Chip key={item} label={item} size="small" className="ingredient-chip" />
                              ))}
                            </Stack>
                          )}
                          {!!insight.saferAlternatives?.length && (
                            <Typography variant="body2" sx={{ mt: 1.2 }}>
                              Safer dish suggestions: {insight.saferAlternatives.join(', ')}
                            </Typography>
                          )}
                        </Alert>
                      );
                    })}
                  </Stack>
                </Box>
              )}

              <Divider sx={{ my: 2.5 }} />

              <Box className="result-block">
                <Typography className="mini-title">Related recipe blogs/articles</Typography>
                {relatedArticles.length === 0 ? (
                  <Typography className="muted-text">
                    No local related articles found yet. Add one from the Articles page.
                  </Typography>
                ) : (
                  <Box className="article-list-grid">
                    {relatedArticles.map((article) => (
                      <Card key={article.id} variant="outlined" className="article-item-card">
                        <CardContent>
                          <Typography variant="h6">{article.title}</Typography>
                          <Typography variant="body2" sx={{ opacity: 0.72, mb: 1 }}>
                            Recipe: {article.recipeTitle}
                          </Typography>
                          {article.imageUrl && (
                            <Box component="img" src={fullImageUrl(article.imageUrl)} alt={article.title} className="article-image" />
                          )}
                          <Typography variant="body2">{article.summary || article.content}</Typography>
                        </CardContent>
                      </Card>
                    ))}
                  </Box>
                )}
              </Box>
            </>
          )}
        </Paper>
      )}
    </>
  );

  const renderHomePage = () => (
    <>
      <section className="home-main-big-box-section">
        <Paper className="home-main-big-box home-dashboard-shell" elevation={0}>
          <Box className="home-dashboard-grid">
            <Box className="home-dashboard-main">
              <Box className="home-hero-panel refined-home-hero">
                <Typography className="page-kicker home-kicker">Recipe recommendation made simple</Typography>
                <Typography className="home-hero-title compact-home-title">
                  Find a recipe from the ingredients you already have.
                </Typography>
                <Typography className="home-hero-text compact-home-text">
                  A cleaner cooking assistant to predict dishes faster, review safety guidance, and browse related content without scanning through cluttered sections.
                </Typography>

                <Box className="hero-cta-row">
                  <Button className="primary-action-btn" onClick={() => document.getElementById('predictor-form')?.scrollIntoView({ behavior: 'smooth' })}>
                    Start predicting
                  </Button>
                  {!user && (
                    <Button className="secondary-action-btn" onClick={() => setCurrentView('signup')}>
                      Create account
                    </Button>
                  )}
                </Box>

                <Box className="home-metric-row compact-metric-row">
                  {quickStats.map((item) => (
                    <Paper key={item.label} className="home-metric-card soft-metric-card" elevation={0}>
                      <Typography className="home-metric-label">{item.label}</Typography>
                      <Typography className="home-metric-value">{item.value}</Typography>
                    </Paper>
                  ))}
                </Box>

                <Box className="ai-preferences-panel">
                  <Typography className="section-title preferences-section-title">Tune smarter recommendations</Typography>
                  <Typography className="section-subtitle">
                    Save allergy profile, favorite cuisines, and diet style to personalize results.
                  </Typography>
                  <Stack spacing={2} sx={{ mt: 2 }} className="preferences-form-stack">
                    <TextField
                      size="small"
                      label="Allergy profile"
                      placeholder="dairy, nuts, gluten"
                      value={allergyProfileInput}
                      onChange={(e) => setAllergyProfileInput(e.target.value)}
                    />
                    <TextField
                      size="small"
                      label="Preferred cuisines"
                      placeholder="indian, italian, mexican"
                      value={preferredCuisineInput}
                      onChange={(e) => setPreferredCuisineInput(e.target.value)}
                    />
                    <TextField
                      size="small"
                      label="Diet preference"
                      placeholder="balanced"
                      value={dietPreferenceInput}
                      onChange={(e) => setDietPreferenceInput(e.target.value)}
                    />
                    <Button className="secondary-action-btn" onClick={handlePreferenceSave}>Save preferences</Button>
                    {preferenceStatus && <Typography className="muted-text">{preferenceStatus}</Typography>}
                  </Stack>
                </Box>
              </Box>

              <Box id="predictor-form" className="home-predictor-panel clean-predictor-panel">
                <Box className="home-panel-header-row">
                  <Box>
                    <Typography className="page-kicker">Predictor</Typography>
                    <Typography className="section-title">Start with ingredients</Typography>
                    <Typography className="section-subtitle">
                      Add ingredients one by one and get a recipe match with confidence, alternatives, and cooking steps.
                    </Typography>
                  </Box>
                  <Chip label={`${ingredients.length} selected`} className="soft-chip" />
                </Box>

                <form onSubmit={handleSubmit} className="simple-input-form home-form-layout">
                  <Box className="simple-input-row home-input-row">
                    <TextField
                      label="Ingredient"
                      value={ingredientInput}
                      variant="outlined"
                      placeholder="For example: tomato, paneer, onion"
                      size="small"
                      onChange={(e) => setIngredientInput(e.target.value)}
                      onKeyDown={handleInputKeyDown}
                      fullWidth
                    />
                    <Button
                      className="dark-action-btn home-add-btn"
                      onClick={handleAddIngredient}
                      disabled={!ingredientInput.trim()}
                      startIcon={<AddIcon />}
                      type="button"
                    >
                      Add
                    </Button>
                  </Box>

                  <Box className="chip-area-clean elevated-chip-area simple-chip-area home-chip-panel">
                    {ingredients.length > 0 ? (
                      <Stack direction="row" spacing={1} className="ingredient-chip-stack">
                        {ingredients.map((ing) => (
                          <Chip
                            key={ing}
                            label={ing}
                            onDelete={() => handleDelete(ing)}
                            deleteIcon={<CloseIcon />}
                            className="ingredient-chip"
                          />
                        ))}
                      </Stack>
                    ) : (
                      <Typography className="muted-text">
                        Add ingredients one by one, then click predict recipe.
                      </Typography>
                    )}
                  </Box>

                  <Button className="submit-main-btn large home-submit-btn" type="submit" fullWidth disabled={loading || ingredients.length === 0}>
                    {loading ? 'Predicting…' : 'Predict recipe'}
                  </Button>
                </form>
              </Box>
            </Box>

            <Box className="home-dashboard-side">
              <Paper className="home-side-panel lighter-side-panel" elevation={0}>
                <Box className="home-panel-header-row compact">
                  <Box>
                    <Typography className="page-kicker">Platform overview</Typography>
                    <Typography className="section-title">What you can do here</Typography>
                  </Box>
                </Box>

                <Box className="home-feature-stack">
                  {featureHighlights.map((feature) => (
                    <Box key={feature.title} className="home-feature-row">
                      <Box className="simple-feature-icon home-feature-icon">{feature.icon}</Box>
                      <Box>
                        <Typography className="info-card-title">{feature.title}</Typography>
                        <Typography className="info-card-text">{feature.text}</Typography>
                      </Box>
                    </Box>
                  ))}
                </Box>

                <Box className="home-tools-grid compact-tools-grid">
                  {infoCards.map((card) => (
                    <Paper key={card.title} className="home-tool-item" elevation={0}>
                      <Box className="info-icon-wrap home-tool-icon">{card.icon}</Box>
                      <Typography className="info-card-title">{card.title}</Typography>
                      <Typography className="info-card-text">{card.text}</Typography>
                    </Paper>
                  ))}
                </Box>
              </Paper>
            </Box>
          </Box>
        </Paper>
      </section>

      {renderPredictionResults()}
    </>
  );

  const renderLoginPage = () => (
    <section className="single-page-section">
      <Paper className="single-form-card auth-card" elevation={0}>
        <Typography className="page-kicker">Login</Typography>
        <Typography className="section-title">Sign in to your account</Typography>
        <Typography className="section-subtitle">Access saved history, article publishing, and your recipe account.</Typography>

        <form onSubmit={(e) => submitAuth('login', e)}>
          <Stack spacing={2.2} sx={{ mt: 3 }}>
            <TextField label="Email Address" value={authEmail} onChange={(e) => setAuthEmail(e.target.value)} fullWidth />
            <TextField label="Password" type="password" value={authPassword} onChange={(e) => setAuthPassword(e.target.value)} fullWidth />
            <Button type="submit" className="submit-main-btn" disabled={authLoading}>
              {authLoading ? 'Please wait...' : 'Login now'}
            </Button>
          </Stack>
        </form>

        {authError && <Alert severity="error" sx={{ mt: 2.5 }}>{authError}</Alert>}
        {user && <Alert severity="success" sx={{ mt: 2.5 }}>Logged in as {user.name} ({user.email})</Alert>}
      </Paper>
    </section>
  );

  const renderSignupPage = () => (
    <section className="single-page-section">
      <Paper className="single-form-card auth-card" elevation={0}>
        <Typography className="page-kicker">Signup</Typography>
        <Typography className="section-title">Create your account</Typography>
        <Typography className="section-subtitle">Create an account to save predictions and publish helpful food content.</Typography>

        <form onSubmit={(e) => submitAuth('signup', e)}>
          <Stack spacing={2.2} sx={{ mt: 3 }}>
            <TextField label="Full Name" value={authName} onChange={(e) => setAuthName(e.target.value)} fullWidth />
            <TextField label="Email Address" value={authEmail} onChange={(e) => setAuthEmail(e.target.value)} fullWidth />
            <TextField label="Password" type="password" value={authPassword} onChange={(e) => setAuthPassword(e.target.value)} fullWidth />
            <Button type="submit" className="submit-main-btn" disabled={authLoading}>
              {authLoading ? 'Please wait...' : 'Create account'}
            </Button>
          </Stack>
        </form>

        {authError && <Alert severity="error" sx={{ mt: 2.5 }}>{authError}</Alert>}
        {user && <Alert severity="success" sx={{ mt: 2.5 }}>Logged in as {user.name} ({user.email})</Alert>}
      </Paper>
    </section>
  );

  const renderArticlesPage = () => (
    <section className="page-stack-section articles-layout">
      <Paper className="section-card article-form-card" elevation={0}>
        <Typography className="page-kicker">Articles</Typography>
        <Typography className="section-title">Create recipe article</Typography>
        <Typography className="section-subtitle">Write and publish recipe articles with image upload and clean formatting.</Typography>
        <form onSubmit={handleArticleSubmit}>
          <Stack spacing={2} sx={{ mt: 2.5 }}>
            <TextField label="Recipe title" value={articleRecipeTitle} onChange={(e) => setArticleRecipeTitle(e.target.value)} />
            <TextField label="Article title" value={articleTitle} onChange={(e) => setArticleTitle(e.target.value)} />
            <TextField label="Short summary" value={articleSummary} onChange={(e) => setArticleSummary(e.target.value)} />
            <TextField label="Content" value={articleContent} onChange={(e) => setArticleContent(e.target.value)} multiline minRows={4} />
            <TextField label="Tags (comma separated)" value={articleTags} onChange={(e) => setArticleTags(e.target.value)} />
            <Button variant="outlined" component="label" className="upload-btn-clean">
              {articleImage ? articleImage.name : 'Upload recipe image'}
              <input hidden type="file" accept="image/*" onChange={(e) => setArticleImage(e.target.files?.[0] || null)} />
            </Button>
            <Button type="submit" className="submit-main-btn">Publish article</Button>
          </Stack>
        </form>
        {articleStatus && <Alert severity="success" sx={{ mt: 2 }}>{articleStatus}</Alert>}
        {articleError && <Alert severity="error" sx={{ mt: 2 }}>{articleError}</Alert>}
      </Paper>

      <Paper className="section-card" elevation={0}>
        <Typography className="section-title">All recipe articles</Typography>
        <Typography className="section-subtitle">Browse available content in a cleaner card-based reading layout.</Typography>
        <Box className="article-list-grid single-column spacious-articles">
          {articles.map((article) => (
            <Card key={article.id} variant="outlined" className="article-item-card enhanced-article-card">
              <CardContent>
                <Typography variant="h6">{article.title}</Typography>
                <Typography variant="body2" sx={{ opacity: 0.72 }}>
                  Recipe: {article.recipeTitle} • By {article.authorName || 'Unknown'}
                </Typography>
                {article.imageUrl && <Box component="img" src={fullImageUrl(article.imageUrl)} alt={article.title} className="article-image" />}
                <Typography variant="body2" sx={{ mt: 1.2 }}>{article.summary}</Typography>
                <Typography variant="body2" sx={{ mt: 1 }}>{article.content}</Typography>
                {!!article.tags?.length && (
                  <Stack direction="row" spacing={1} sx={{ mt: 1.4, flexWrap: 'wrap' }}>
                    {article.tags.map((tag: string) => <Chip key={tag} label={tag} size="small" className="ingredient-chip" />)}
                  </Stack>
                )}
              </CardContent>
            </Card>
          ))}
          {articles.length === 0 && <Typography className="muted-text">No articles added yet.</Typography>}
        </Box>
      </Paper>
    </section>
  );

  const renderHistoryPage = () => (
    <section className="single-page-section history-page-wrap">
      <Paper className="single-form-card history-card" elevation={0}>
        <Typography className="page-kicker">History</Typography>
        <Typography className="section-title">Prediction history</Typography>
        <Typography className="section-subtitle">Review your previously predicted dishes in a cleaner timeline-like list.</Typography>
        {!user && <Alert severity="info" sx={{ mt: 2 }}>Login first to store and view your prediction history.</Alert>}
        {user && history.length === 0 && <Typography className="muted-text" sx={{ mt: 2 }}>No history yet.</Typography>}
        <List className="history-list-clean">
          {history.map((item) => (
            <ListItem key={item.id} divider className="history-list-item-clean">
              <ListItemText
                primary={`${item.prediction} (${(item.ingredients || []).join(', ')})`}
                secondary={`Alternatives: ${(item.alternatives || []).join(', ') || 'N/A'}`}
              />
            </ListItem>
          ))}
        </List>
      </Paper>
    </section>
  );

  return (
    <Box className="app-shell-clean">
      <Box className="background-orb orb-left" />
      <Box className="background-orb orb-right" />

      <Box component="header" className="top-navbar-clean">
        <Container maxWidth={false} className="app-container-wide navbar-container-wide">
          <Box className="navbar-inner-clean">
            <Box className="brand-area-clean" onClick={() => setCurrentView('home')} role="button" tabIndex={0}>
              <Box className="brand-logo-clean">F</Box>
              <Box>
                <Typography className="brand-title-clean">FlavorFusion</Typography>
                <Typography className="brand-subtitle-clean">Recipe prediction assistant</Typography>
              </Box>
            </Box>

            <Box className="nav-links-clean">
              {navItems.map((item) => (
                <Button
                  key={item.key}
                  startIcon={item.icon}
                  className={currentView === item.key ? 'nav-link-btn active' : 'nav-link-btn'}
                  onClick={() => setCurrentView(item.key)}
                >
                  {item.label}
                </Button>
              ))}
            </Box>

            <Box className="nav-user-actions">
              {user ? (
                <>
                  <Chip label={`Hi, ${user.name}`} className="soft-chip" />
                  <Button className="logout-btn-clean" onClick={handleLogout}>Logout</Button>
                </>
              ) : (
                <Button className="primary-action-btn small" onClick={() => setCurrentView('login')}>Get started</Button>
              )}
            </Box>
          </Box>
        </Container>
      </Box>

      <Container maxWidth={false} className="main-content-clean app-container-wide">
        {currentView === 'home' && renderHomePage()}
        {currentView === 'login' && renderLoginPage()}
        {currentView === 'signup' && renderSignupPage()}
        {currentView === 'articles' && renderArticlesPage()}
        {currentView === 'history' && renderHistoryPage()}
      </Container>

      <Dialog open={stepsOpen} onClose={() => setStepsOpen(false)} fullWidth maxWidth="sm">
        <DialogTitle>Cooking steps: {stepsTitle}</DialogTitle>
        <DialogContent dividers>
          {stepsLoading && <Typography>Loading…</Typography>}
          {!stepsLoading && stepsError && <Alert severity="error">{stepsError}</Alert>}
          {!stepsLoading && !stepsError && (
            <>
              {sourceUrl && (
                <Typography variant="body2" sx={{ mb: 1.5 }}>
                  Source: <a href={sourceUrl} target="_blank" rel="noreferrer">{sourceUrl}</a>
                </Typography>
              )}
              {steps.length > 0 ? (
                <List>
                  {steps.map((s, i) => (
                    <ListItem key={i} disableGutters>
                      <ListItemText primary={`${i + 1}. ${s}`} />
                    </ListItem>
                  ))}
                </List>
              ) : (
                <Typography variant="body2">No step-by-step instructions returned from Spoonacular.</Typography>
              )}
            </>
          )}
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setStepsOpen(false)}>Close</Button>
        </DialogActions>
      </Dialog>
    </Box>
  );
}

export default App;