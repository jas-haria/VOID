import { ActivatedRoute, Router } from '@angular/router';
import { Component, OnInit, OnDestroy } from '@angular/core';
import { formatDate } from '@angular/common';
import { QuoraService } from '../quora.service';
import { Page } from 'src/app/shared/models/page.model';
import { PageEvent } from '@angular/material/paginator';
import { QuoraQuestion } from 'src/app/shared/models/quora-question.model';
import { Subscription, Subject } from 'rxjs';
import { Division } from 'src/app/shared/models/division.model';
import { DivisionService } from 'src/app/division/division.service';
import { FormControl, Validators } from '@angular/forms';
import { TimePeriod } from 'src/app/shared/models/enums/time-period.enum';
import { ApiService } from 'src/app/shared/services/api.service';

@Component({
  selector: 'app-questions-table',
  templateUrl: './questions-table.component.html',
  styleUrls: ['./questions-table.component.scss']
})
export class QuestionsTableComponent implements OnInit, OnDestroy {

  subscription: Subscription = new Subscription();
  dataSource: any[] = [];
  totalLength: number = 0;
  pageSizeOptions: number[] = [10, 15, 20];
  displayedColumns = ["id", "question_text", "division_name", "asked_on" ];
  displayedColumnsWidth = {"id": 10, "question_text": 50, "division_name": 15, "asked_on": 15}; //remaining 5 for checkbox
  displayedColumnsHeaders = ["ID", "Question", "Division", "Asked On"];
  isCheckbox = true;
  selected: QuoraQuestion[] = [];
  divisions: Division[] = [];
  timePeriodEnumArray: TimePeriod[] = Object.values(TimePeriod) 
  divisionFormControl = new FormControl([], Validators.required);
  selectedDivisions: number[] = [];
  selectedTimePeriod: TimePeriod = TimePeriod.WEEK;
  selectedEvaluation: boolean = false;
  selectedPage: number = 0;
  selectedSize: number = this.pageSizeOptions[0];
  clearSelect: Subject<void> = new Subject<void>()
    
  constructor(private _route: ActivatedRoute,
    private _router: Router,
    private _quoraService: QuoraService,
    private _divisionService: DivisionService,
    private _apiService: ApiService) {}

  ngOnInit(): void {
    this.subscription.add(
      this._divisionService.getAllDivision().subscribe((response: Division[]) => {
        this.initialiseDivisions(response);
        this.routeListner();
      })
    );
  }

  ngOnDestroy(): void {
    this.subscription.unsubscribe();
  }

  routeListner(): void {
    this.subscription.add(
      this._route.queryParams.subscribe(params => {
        if (null == params['page'] || null == params['size'] || null == params['divisions'] 
        || null == params['evaluated'] || null == params['timePeriod']) {
          let parameters = this.setUrlParameters(1, this.pageSizeOptions[0], this.selectedDivisions,
             this.selectedEvaluation, this.selectedTimePeriod);
          this._router.navigate([this._router.url.split("?")[0]], {queryParams: parameters});
        }
        else {
          this.selectedSize = this.pageSizeOptions.includes(Number(params['size']))? Number(params['size']): this.pageSizeOptions[0];
          this.selectedPage = Number(params['page']) > 0? Number(params['page']) - 1: 0; // -1 because first page on server is 0
          this.selectedDivisions = JSON.parse(params['divisions']);
          this.selectedEvaluation = params['evaluated'] == 'false'? false: true;
          this.selectedTimePeriod = this.getTimePeriod(params['timePeriod']);
          this.divisionFormControl.setValue(this.divisions.filter(val => this.selectedDivisions.includes(Number(val.id))));
          this.refreshDataSource();
        }
      })
    );
  }

  refreshDataSource(): void {
    this.subscription.add(
      this._quoraService.getQuestions(this.selectedPage, this.selectedSize, this.selectedDivisions, this.selectedEvaluation, this.selectedTimePeriod).subscribe((response: Page<QuoraQuestion>) => {
        this.dataSource = response.content.map(question =>  this.mapQuestionForTable(question));
        this.totalLength = response.totalLength;
      })
    );
  }

  refreshData(): void {
    this.clearSelect.next();
    this.selectedDivisions = this.getIdsFromArray(this.divisionFormControl.value);
    let parameters = this.setUrlParameters(1, this.selectedSize, this.selectedDivisions, this.selectedEvaluation, this.selectedTimePeriod)
    this._router.navigate([this._router.url.split('?')[0]], {queryParams: parameters});
  }

  pageUpdateEvent(pageEvent: PageEvent): void {
    let parameters = this.setUrlParameters(pageEvent.pageIndex + 1, pageEvent.pageSize, this.selectedDivisions, this.selectedEvaluation, this.selectedTimePeriod)
    this._router.navigate([this._router.url.split('?')[0]], {queryParams: parameters});
  }

  selectionEvent(selected: QuoraQuestion[]): void {
    this.selected = selected;
  }

  setUrlParameters(page: number, size: number, divisions: number[], evaluated: boolean, timePeriod: TimePeriod): any {

    return {
      'page': page,
      'size': size,
      'divisions': JSON.stringify(divisions),
      'evaluated': evaluated,
      'timePeriod': timePeriod
    }
  }

  mapQuestionForTable(question: QuoraQuestion): any {
    return {
      'id': question.id,
      'question_text': question.question_text,
      'question_url': question.question_url,
      'division_name': this.divisions.filter(division => division.id == question.division_id)[0].division,
      'evaluated': question.evaluated,
      'asked_on': formatDate(question.asked_on, 'MMM dd, yyyy', 'en-US')
    }
  }

  initialiseDivisions(divisions: Division[]): void {
    this.divisions = divisions;
    this.divisionFormControl.patchValue(divisions);
    this.selectedDivisions = this.getIdsFromArray(divisions);
  }

  updateEvaluationData(): void {
    this.subscription.add(
      this._quoraService.updateQuestionsEvaluation(this.getIdsFromArray(this.selected), !this.selectedEvaluation).subscribe(response => {
        this.clearSelect.next();
        this.refreshDataSource();
      })
    );
  }

  deleteQuestions(): void {
    this.subscription.add(
      this._quoraService.deleteQuestions(this.getIdsFromArray(this.selected)).subscribe(response => {
        this.clearSelect.next();
        this.refreshDataSource();
      })
    );
  }

  getIdsFromArray(arr: any[]): number[] {
    var result = [];
    arr.forEach(element => {
      result.push(element.id);
    })
    return result;
  }

  getTimePeriod(time: string): TimePeriod {
      switch(time) {
        case 'day': return TimePeriod.DAY
        case 'week': return TimePeriod.WEEK
        case 'month': return TimePeriod.MONTH
      }
  }

  updateTimeData(eventValue: TimePeriod): void {
    this.selectedTimePeriod = eventValue;
    this.refreshData();
  }

  updateDivisionsData(): void {
    if (this.divisionFormControl.valid) {
      this.refreshData();
    }
  }

  updateEvaluationToggleData(eventChecked: boolean): void {
    this.selectedEvaluation = eventChecked;
    this.refreshData();
  }

}
