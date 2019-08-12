from typing import Optional

import numpy as np

from genetic_algorithm.utils.model_maker import ModelMaker
from genetic_algorithm.utils.model_scorer import ModelScorer

class GeneticAlgorithm:
    def __init__(
        self, 
        modelMaker: ModelMaker,
        modelScorer: ModelScorer,
        popSize: int,
        keepTopFrac: float,
        keepBtmFrac: float,
        makeChildFrac: float,
        mutateFrac: float,
        keepGraveyard: bool = False,
        randomState: Optional[int] = None
    ):
        '''
        Genetic algorithm for scikit-learn model hyperparameter tuning 
        -----
        params
            :modelMaker: instance of class ModelMaker
            :modelScorer: instance of class ModelScorer
            :popSize: number of models in a generation
            :keepTopFrac: fraction of models in a generation to keep from top performers
            :keepBtmFrac: fraction of models in a generation to keeep from rest (randomized)
            :makeChildFrac: fraction of new models to spawn in a generation
            :mutateFrac: fraction of models to mutate in a generation
            :keepGraveyard: whether to keep a list of all trained models over generations
            :randomState: seed for random initializations
        public methods
            :evolve: evolve a population of models using genetic algorithm techniques
        public attributes
            :self.population: final population of models
            :self.bestModel: best model after all iterations
            :self.graveYard: discarded models from previous generations (if kept)
        '''
        assert keepTopFrac + keepBtmFrac + makeChildFrac <= 1        
        
        self.modelMaker = modelMaker
        self.modelScorer = modelScorer
        
        self.popSize = popSize
        self.keepTopFrac = keepTopFrac
        self.keepBtmFrac = keepBtmFrac
        self.makeChildFrac = makeChildFrac
        self.mutateFrac = mutateFrac
        self.keepGraveyard = keepGraveyard
        self.randomState = randomState
        
        self.keepTopN = int(np.floor(self.keepTopFrac * self.popSize))
        self.keepBtmN = int(np.floor(self.keepBtmFrac * self.popSize))
        self.makeChildN = int(np.floor(self.makeChildFrac * self.popSize))
        self.mutateN = int(np.floor(self.mutateFrac * self.popSize))
        
        if self.keepGraveyard:
            self.graveyard = []
            
        self.population = []
        self.bestModel = None   
        
        if self.randomState is not None:
            np.random.seed(self.randomState)
        return None
            
    def evolve(
        self, 
        maxIters: Optional[int] = 10, 
        maxItersNoImprov: Optional[int] = None, 
        printCurrentBest: bool = False
    ) -> None:
        '''
        Evolve the population until a stopping condition is met
        -----
        params:
            maxIters: maximum number of generations to evolve
            maxItersNoImprov: maximum number of consecutive 
                              generations to evolve without improvement
            printCurrentBest: log best loss after each evolution round
        void
        '''
        assert maxIters is not None or maxItersNoImprov is not None  # otherwise will run forever
        
        if len(self.population) == 0:
            self._initializePop()
            
        iters = 0
        itersNoImprov = 0
            
        stopCond = False
        if maxIters is not None and itersNoImprov is not None:
            stopCond = iters == maxIters or itersNoImprov == maxItersNoImprov             
        elif maxIters is not None:
            stopCond = iters == maxIters
        elif itersNoImprov is not None:
            stopCond = itersNoImprov == maxItersNoImprov
        else:
            raise Exception('Invalid stopCond')
        
        while not stopCond:
            self._scoreModelsInPop()
            bestModel = self._getBestModel()
            
            if self.bestModel is None or (
                bestModel.fitness > self.bestModel.fitness
            ):
                self.bestModel = bestModel
                itersNoImprov = 0
            else:
                itersNoImprov += 1
            iters += 1
            
            if printCurrentBest:
                print(f'Current best fitness: {self.bestModel.fitness}')
                
            self._killUnfit()
            self._makeChildren()
            self._makeRemainingRandomModels()
            
        print(
            f'Evolved {iters} generations ({itersNoImprov} generations '
            + 'without improvement)'
        )
        return None
    
    def _initializePop(self) -> None:
        assert len(self.population) == 0, 'Models already in population'
        self.population = [
            self.modelMaker.makeRandomModel() for m in range(self.popSize)
        ]
        return None
        
    def _scoreModelsInPop(self) -> None:
        for m in range(len(self.population)):
            if self.population[m].fitness is None:
                self.population[m].fitness = (
                    self.modelScorer.scoreModel(self.population[m])
                )
        return None
    
    def _getBestModel(self):
        self._sortPopByFitness()
        bestModel = self.population.copy()[0]
        return bestModel
        
    def _killUnfit(self) -> None:
        self._sortPopByFitness()

        topKeepInds = range(self.keepTopN)
        topKeepMods = [self.population[i] for i in topKeepInds]
        
        remainingInds = [i for i in range(len(self.population)) if i not in topKeepInds]
        btmKeepInds = np.random.choice(
            remainingInds, size=self.keepBtmN, replace=False
        )
        btmKeepMods = [self.population[i] for i in btmKeepInds]

        assert len(set(topKeepInds).intersection(set(btmKeepInds))) == 0, (
            'Cannot have overlap in top kept models and bottom kept models'
        )
        
        keepMods = [*topKeepMods, *btmKeepMods]
        unfitMods = [m for m in self.population if m not in keepMods]
        
        self.population = keepMods
        if self.keepGraveyard:
            self.graveyard += unfitMods
        return None
        
    def _sortPopByFitness(self) -> None:
        self.population.sort(key=lambda m: m.fitness, reverse=True)
        return None
    
    def _makeChildren(self) -> None:
        children = []
        for i in range(self.makeChildN):
            mother, father = np.random.choice(self.population, size=2, replace=False)
            child = self.modelMaker.makeChildModel(mother, father)
            children.append(child)
        
        childToMutate = np.random.choice(children)
        self.modelMaker.mutateModel(childToMutate)
        
        self.population += children
        return None
    
    def _makeRemainingRandomModels(self) -> None:
        while len(self.population) < self.popSize:
            self.population.append(self.modelMaker.makeRandomModel())
        return None

        
# class ModelMaker:
#     '''
#     Class to make scikit-learn pipeline models
#     -----
#     params
#         :pipelineMaker: scikit-learn pipeline maker
#         :estimatorType: supervised estimator (maps to scikit-learn estimator class)
#         :preprocessorChoiceGridOverrides: optional preprocessor choice grids 
#                                           to override defaults
#         :estimatorChoiceGridOverrides: optional estimator choice grids 
#                                        to override defaults
#     public methods
#         :makeRandomModel: Makes random model based on choice grids
#         :makeChildModel: Makes model by randomly combining hyperparameters
#                          of two models
#         :mutateModel: Mutate a model by randomly changing n of its hyperparameters
#     '''
#     def __init__(
#         self, 
#         pipelineMaker: PipelineMaker,
#         estimatorType: str,
#         preprocessorChoiceGridOverrides: Optional[Dict[str, list]] = None,
#         estimatorChoiceGridOverrides: Optional[Dict[str, list]] = None,
#     ):
#         self.pipelineMaker = pipelineMaker
#         self.estimatorType = estimatorType
#         self.preprocessorChoiceGridOverrides = preprocessorChoiceGridOverrides
#         self.estimatorChoiceGridOverrides = estimatorChoiceGridOverrides
        
#         if self.estimatorType == 'gbm_regressor':
#             self.estimatorClass = GradientBoostingRegressor
#             self.estimatorChoiceGrid = self.gbmRegressorChoiceGrid
#         elif self.estimatorType == 'rf_regressor':
#             self.estimatorClass = RandomForestRegressor
#             self.estimatorChoiceGrid = self.rfRegressorChoiceGrid
#         elif self.estimatorType == 'enet_regressor':
#             self.estimatorClass = ElasticNet
#             self.estimatorChoiceGrid = self.enetRegressorChoiceGrid
#         elif self.estimatorType == 'gbm_classifier':
#             self.estimatorClass = GradientBoostingClassifier
#             self.estimatorChoiceGrid = self.gbmClassifierChoiceGrid
#         elif self.estimatorType == 'rf_classifier':
#             self.estimatorClass = RandomForestClassifier
#             self.estimatorChoiceGrid = self.rfClassifierChoiceGrid
#         elif self.estimatorType == 'enet_classifier':
#             self.estimatorClass = SGDClassifier
#             self.estimatorChoiceGrid = self.enetClassifierChoiceGrid
            
#         if self.preprocessorChoiceGridOverrides is not None:
#             self.preprocessorChoiceGrid = {
#                 **self.preprocessorChoiceGrid, 
#                 **self.preprocessorChoiceGridOverrides
#             }
#         if self.estimatorChoiceGridOverrides is not None:
#             self.estimatorChoiceGrid = {
#                 **self.estimatorChoiceGrid,
#                 **self.estimatorChoiceGridOverrides
#             }
    
#     def makeRandomModel(self):
#         preprocessorChoices = {
#             param: np.random.choice(self.preprocessorChoiceGrid[param])
#             for param in self.preprocessorChoiceGrid.keys()
#         }
#         estimatorChoices = {
#             param: np.random.choice(self.estimatorChoiceGrid[param])
#             for param in self.estimatorChoiceGrid.keys()
#         }
#         randomModel = self.pipelineMaker.makePipeline(
#             preprocessorChoices, estimatorChoices
#         )
#         return randomModel
    
#     def makeChildModel(self, mother, father):
#         preprocessorChoices = {
#             param: np.random.choice(
#                 *mother.preprocessorChoiceGrid[param],
#                 *father.preprocessorChoiceGrid[param]
#             ) for param in self.preprocessorChoiceGrid.keys()
#         }
#         estimatorChoices = {
#             param: np.random.choice(
#                 *mother.estimatorChoiceGrid[param],
#                 *father.estimatorChoiceGrid[param]
#             ) for param in self.estimatorChoiceGrid.keys()
#         }
#         childModel = self.pipelineMaker.makePipeline(
#             preprocessorChoices, estimatorChoices
#         )
#         return childModel
    
# #     def _makeModel(
# #         self, preprocessorChoices: list, estimatorChoices: list
# #     ) -> sklearn.pipeline.Pipeline:
# #         pipeline = self.pipelineMaker.makePipeline(
# #             preprocesorChoices, estimatorChoices
# #         )
# #         return pipeline
        
#     preprocessorChoiceGrid = {
#         'numImputerStrat': ['mean', 'median'],
#         'catEncoderStrat': ['oneHot', 'targetMean'],
#         'missingValues': [np.nan, 'DO_NOT_FLAG_MISSING'],
#         'tmePriorFrac': np.linspace(0.01, 1, num=100)
#     }
#     gbmRegressorChoiceGrid = {
#         'loss': ['ls', 'lad'],
#         'n_estimators': np.arange(100, 1000, 100),
#         'subsample': np.linspace(0.1, 1, num=10),
#         'min_samples_leaf': np.arange(1, 10),
#         'max_depth': np.arange(1, 12),
#         'min_impurity_decrease': np.linspace(0, 1, num=10)
#     }
#     rfRegressorChoiceGrid = {
#         'criterion': ['mse', 'mae'],
#         'max_features': ['sqrt', 'log2', None],
#         'n_estimators': np.arange(100, 1000, 100)
#     }
#     enetRegressorChoiceGrid = {
#         # sklearn advises against including very small alpha values
#         'alpha': np.linspace(0.01, 1, num=100), 
#         'l1_ratio': np.concatenate(
#             [np.logspace(-3, -1, num=4), np.linspace(0, 1, num=100)]
#         )
#     }
#     gbmClassifierChoiceGrid = {
#         'learning_rate': np.linspace(0.01, 1, num=100),
#         'n_estimators': np.arange(100, 1000, 100),
#         'subsample': np.linspace(0.1, 1, num=10),
#         'min_samples_leaf': np.arange(2, 10),
#         'max_depth': np.arange(1, 12),
#         'min_impurity_decrease': np.linspace(0, 1, num=10)        
#     }
#     rfClassifierChoiceGrid = {
#         'criterion': ['gini', 'entropy'],
#         'max_features': ['sqrt', 'log2', None],
#         'n_estimators': np.arange(100, 1000, 100)
#     }
#     enetClassifierChoiceGrid = {
#         'loss': ['hinge', 'log'],
#         'alpha': np.concatenate(
#             [np.logspace(-4, -2, num=3), np.linspace(0.1, 1, num=100)]
#         ),
#         'l1_ratio': np.concatenate(
#             [np.logspace(-4, -1, num=4), np.linspace(0, 1, num=100)]
#         ),
#         'learning_rate': ['constant', 'optimal', 'invscaling', 'adaptive'],
#         'eta0': np.concatenate(
#             [np.logspace(-4, -2, num=3), np.linspace(0.1, 1, num=100)]
#         ),
#         'power_t': np.concatenate(
#             [np.logspace(-4, -2, num=3), np.linspace(0.1, 1, num=100)]
#         ),
#         'penalty': ['elastic_net']
#     }


# class ModelScorer:
#     '''
#     Class to evaluate model accuracy given data and evaluation criteria
#     -----
#     params
#         :estimator: scikit-learn estimator or pipeline
#         :X: input data array
#         :y: target data array
#         :scoring: metric to evaluate model accuracy
#         :crossValidator: scikit-learn cross validation scheme
#         :errorScore: how to score CV folds that encounter errors
#     public methods
#         :scoreModel: Evaluate model accuracy, given data and evaluation criteria
#     '''
#     def __init__(
#         self,
#         estimator: Pipeline,
#         X: np.array,
#         y: np.array,
#         evalMetric,
#         crossValidator,
#         errorScore=np.nan
#     ):
#         self.estimator = estimator
#         self.X = X
#         self.y = y
#         self.scoring = scoring
#         self.crossValidator = crossValidator
#         self.evalMetric = evalMetric
#         return None
    
#     def scoreModel(self, aggregator: str = 'mean') -> float:
#         '''
#         score model using scikit-learn's cross_val_score
#         -----
#         params
#             :aggregator: how to extract single metric from array of CV fold scores
#         returns
#             model score (float)
#         '''
#         crossValScores = cross_val_score(
#             estimator=self.estimator, X=X, y=y, scoring=self.evalMetric,
#             cv=self.crossValidator, error_score=self.errorScore
#         )
#         if aggregator == 'mean':
#             modelScore = self._getMeanCrossValScore(crossValScores)
#         return modelScore
    
#     def _getMeanCrossValScore(self, crossValScores: np.array) -> float:
#         meanCrossValScore = (
#             crossValScores.mean() 
#             if not np.isnan(crossValScores).all() else np.NINF
#         )
#         return meanCrossValScore
        

# class PipelineMaker:
#     def __init__(
#         self,
#         estimatorClass,
#         numFeatures: List[str],
#         catFeatures: List[str],
#         randomState: Optional[int] = None
#     ):
#         self.estimatorClass = estimatorClass
#         self.numFeatures = numFeatures
#         self.catFeatures = catFeatures
#         self.randomState = randomState
#         return None
    
#     def makePipeline(
#         self,
#         preprocessorChoices: list,
#         estimatorChoices: list
#     ) -> sklearn.pipeline.Pipeline:
        
#         preprocessor = self._makePreprocessor(**preprocessorChoices)
#         estimator = self._makeEstimator(estimatorChoices)
#         pipeline = Pipeline([
#             ('preprocessor', preprocessor),
#             ('estimator', estimator)
#         ])
#         return pipeline
    
#     def _makePreprocessor(
#         self, 
#         numImputerStrat: str = 'mean',
#         catEncoderStrat: str = 'oneHot',
#         missingValues: Union[float, str] = np.nan,
#         tmePriorFrac: Optional[float] = None
#     ) -> FeatureUnion:
        
#         catEncoder = self._getCatEncoder(catEncoderStrat)
#         numPipe = Pipeline([
#             ('numImputer', SimpleImputer(strategy=numImputerStrat)),
#             ('numScaler', StandardScaler())
#         ])
#         catPipe = Pipeline([
#             ('catImputer', SimpleImputer(strategy='most_frequent')),
#             ('catEncoder', catEncoder)
#         ])
#         numCatPipe = ColumnTransformer([
#             ('numPipe', numPipe, self.numFeatures),
#             ('catPipe', catPipe, self.catFeatures)
#         ])
#         preprocessor = FeatureUnion([
#             ('numCatPipe', numCatPipe),
#             ('missingFlagger', 
#              MissingIndicator(missing_values=missingValues, features='all')
#             )
#         ])
#         return preprocessor
        
#     @staticmethod
#     def _getCatEncoder(
#         catEncoderStrat: str, 
#         tmePriorFrac: Optional[float] = None
#     ) -> Optional[OneHotEncoder, TargetMeanEncoder]:
        
#         if catEncoderStrat == 'oneHot':
#             catEncoder = OneHotEncoder(handle_unknown='ignore')
#         elif catEncoderStrat == 'targetMean':
#             catEncoder = TargetMeanEncoder(prior_frac=tmePriorFrac)
#         return catEncoder
        
#     def _makeEstimator(
#         self, 
#         estimatorChoices: dict,
#     ): # make conditional based on estimator class
#         estimator = self.estimatorClass(
#             **estimatorChoices, random_state=self.randomState
#         )
#         return estimator
    