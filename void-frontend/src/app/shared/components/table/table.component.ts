import { Component, OnInit, Input, AfterViewInit, ViewChild, Output, EventEmitter, OnDestroy } from '@angular/core';
import { MatPaginator, PageEvent } from '@angular/material/paginator';
import { SelectionModel } from '@angular/cdk/collections';
import { MatRow } from '@angular/material/table';
import { Subscription, Observable } from 'rxjs';

@Component({
  selector: 'app-table',
  templateUrl: './table.component.html',
  styleUrls: ['./table.component.scss']
})
export class TableComponent implements OnInit, AfterViewInit, OnDestroy {

  subscription: Subscription = new Subscription();
  @ViewChild('paginator') public paginator: MatPaginator;
  @Input('displayedColumnsHeaders') public displayedColumnsHeaders: string[];
  @Input('displayedColumns') public displayedColumns: string[];
  @Input('displayedColumnsWidth') public displayedColumnsWidth: {};
  @Input('dataSource') public dataSource: any[];
  @Input('totalLength') public totalLength: number;
  @Input('pageSizeOptions') public pageSizeOptions: number[];
  @Input('isCheckbox') public isCheckbox: boolean;
  @Input('clearSelect') public clearSelect: Observable<void>;
  @Input('pageIndex') public pageIndex: number;
  @Input('pageSize') public pageSize: number;
  @Output() pageUpdateEvent: EventEmitter<PageEvent> = new EventEmitter();
  @Output() selectionEvent: EventEmitter<any[]> = new EventEmitter();
  specialColumns = ["question_text"];
  selection = new SelectionModel<any>(true, []);
  
  constructor() { }

  ngOnInit(): void {
    this.subscription.add(
      this.clearSelect.subscribe(input => {
        this.selection.clear();
      })
    );
  }

  ngAfterViewInit(): void {
    this.subscription.add(
      this.paginator.page.subscribe((pageEvent: PageEvent) => {
        this.pageUpdateEvent.emit(pageEvent);
      })
    );
  }

  ngOnDestroy(): void {
    this.subscription.unsubscribe();
  }

  getDisplayedColumns(tableDefinition: boolean): string[] {
    if (this.isCheckbox && tableDefinition) {
      return ["select", ...this.displayedColumns];
    }
    return this.displayedColumns;
  }

  masterToggle() {
    this.isAllSelected() ?
        this.selection.clear() :
        this.dataSource.forEach(row => this.selection.select(row));
    this.emitSelectionEvent();
  }

  isAllSelected(): boolean {
    const numSelected = this.selection.selected.length;
    const numRows = this.dataSource.length;
    return numSelected === numRows;
  }

  rowToggle(row: MatRow): void {
    this.selection.toggle(row);
    this.emitSelectionEvent();
  }

  emitSelectionEvent(): void {
    this.selectionEvent.emit(this.selection.selected);
  }

  getColumnWidth(column: string): number {
    if (column && this.displayedColumnsWidth && this.displayedColumnsWidth[column]) {
      return this.displayedColumnsWidth[column];
    }
    return 10;
  }
}
